import uuid
from datetime import datetime, timedelta

from common.db.connection import get_connection
from elastic_search.models import IndexStatus
from flask import request
from google_cloud.pubsub.handler import publish_file_upload_complete
from google_cloud.storage.handler import (
    blob_exists,
    create_resumable_upload_session,
)
from google_cloud.tasks.handler import tasks_defer

from apis.common.auth.handler import auth
from apis.file_handlers.indexer import index_uploaded_file
from apis.file_handlers.utils import (
    get_allowed_content_types,
    get_upload_session_ttl_hours,
    sanitize_filename,
)
from file_handlers.constants import UploadStates


@auth(auth_required=False)
def create_upload_session():
    data = request.get_json(silent=True) or {}

    filename = data.get('filename')
    content_type = data.get('content_type')
    size_bytes = data.get('size_bytes')
    origin = data.get('origin')

    if not filename or not isinstance(filename, str):
        return {'error': 'filename is required'}, 400
    if not content_type or not isinstance(content_type, str):
        return {'error': 'content_type is required'}, 400

    allowed = get_allowed_content_types()
    if allowed is not None and content_type not in allowed:
        return {'error': 'content_type is not allowed'}, 400

    if size_bytes is not None and (not isinstance(size_bytes, int) or size_bytes < 0):
        return {'error': 'size_bytes must be a non-negative integer'}, 400

    if origin is not None and not isinstance(origin, str):
        return {'error': 'origin must be a string'}, 400

    try:
        safe_filename = sanitize_filename(filename)
    except ValueError as exc:
        return {'error': str(exc)}, 400

    session_id = str(uuid.uuid4())
    object_path = f'uploads/{session_id}/{safe_filename}'

    now = datetime.now()
    expires_at = now + timedelta(hours=get_upload_session_ttl_hours())
    created_at_iso = now.isoformat()
    expires_at_iso = expires_at.isoformat()

    try:
        upload_url = create_resumable_upload_session(
            object_path=object_path,
            content_type=content_type,
            origin=origin,
        )
    except ValueError as exc:
        return {'error': str(exc)}, 500
    except Exception as e:
        print(e)
        return {'error': 'Failed to create upload session'}, 500

    conn = get_connection()
    try:
        conn.execute(
            '''
            INSERT INTO upload_sessions (
              id, object_path, filename, content_type, size_bytes,
              status, upload_url, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                session_id,
                object_path,
                safe_filename,
                content_type,
                size_bytes,
                UploadStates.STATUS_PENDING,
                upload_url,
                created_at_iso,
                expires_at_iso,
            ),
        )
        conn.commit()
    except Exception:
        return {'error': 'Failed to persist upload session'}, 500
    finally:
        conn.close()

    return {'session_id': session_id,
            'upload_url': upload_url,
            'object_path': object_path,
            'expires_at': expires_at_iso,
        }, 201


def _load_session(session_id: str):
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT * FROM upload_sessions WHERE id = ?',
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def _update_session(session_id: str, **fields) -> None:
    if not fields:
        return
    assignments = ', '.join(f'{key} = ?' for key in fields)
    values = list(fields.values()) + [session_id]
    conn = get_connection()
    try:
        conn.execute(
            f'UPDATE upload_sessions SET {assignments} WHERE id = ?',
            values,
        )
        conn.commit()
    finally:
        conn.close()


@auth(auth_required=False)
def complete_upload_session():
    data = request.get_json(silent=True) or {}
    session_id = data.get('session_id')
    if not session_id or not isinstance(session_id, str):
        return {'error': 'session_id is required'}, 400

    session = _load_session(session_id)
    if session is None:
        return {'error': 'upload session not found'}, 404

    expires_at = datetime.fromisoformat(session['expires_at'])
    if datetime.now() > expires_at and session['status'] == UploadStates.STATUS_PENDING:
        _update_session(
            session_id,
            status=UploadStates.STATUS_EXPIRED,
            index_status=IndexStatus.FAILED,
            index_error='upload session expired',
        )
        return {'error': 'upload session expired'}, 410

    object_path = session['object_path']
    try:
        exists = blob_exists(object_path)
    except ValueError as exc:
        return {'error': str(exc)}, 500
    except Exception:
        return {'error': 'Failed to verify uploaded object'}, 500

    if not exists:
        _update_session(
            session_id,
            status=UploadStates.STATUS_FAILED,
            index_status=IndexStatus.FAILED,
            index_error='GCS object not found',
        )
        return {'error': 'uploaded object not found'}, 400

    _update_session(
        session_id,
        status=UploadStates.STATUS_COMPLETED,
        index_status=IndexStatus.INDEXING,
        index_error=None,
    )

    payload = {
        'session_id': session_id,
        'object_path': object_path,
        'filename': session['filename'],
    }
    message_id = None
    published = False
    try:
        message_id = publish_file_upload_complete(payload)
        published = True
    except Exception:
        published = False

    if not published:
        tasks_defer(_index_session, session_id, delay_seconds=3)

    return {
        'session_id': session_id,
        'object_path': object_path,
        'status': UploadStates.STATUS_COMPLETED,
        'index_status': IndexStatus.INDEXING,
        'message_id': message_id,
    }, 202


def _index_session(session_id: str) -> int:
    session = _load_session(session_id)
    if session is None:
        raise ValueError('upload session not found')
    chunk_count = index_uploaded_file(
        session_id=session_id,
        object_path=session['object_path'],
        filename=session['filename'],
    )
    indexed_at = datetime.now().isoformat()
    _update_session(
        session_id,
        index_status=IndexStatus.INDEXED,
        indexed_at=indexed_at,
        index_error=None,
        chunk_count=chunk_count,
    )
    return chunk_count


def process_file_upload_complete_message(payload: dict) -> None:
    session_id = payload.get('session_id')
    if not session_id:
        raise ValueError('session_id is required')
    session = _load_session(session_id)
    if session is None:
        raise ValueError('upload session not found')
    if session.get('index_status') == IndexStatus.INDEXED:
        return
    try:
        _index_session(session_id)
    except Exception as exc:
        _update_session(
            session_id,
            index_status=IndexStatus.FAILED,
            index_error=str(exc),
        )
        raise
