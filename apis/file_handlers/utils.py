import os
import re

from apis.file_handlers.constants import DEFAULT_UPLOAD_SESSION_TTL_HOURS


def get_upload_session_ttl_hours() -> int:
    raw = os.environ.get('UPLOAD_SESSION_TTL_HOURS')
    if raw is None:
        return DEFAULT_UPLOAD_SESSION_TTL_HOURS
    return int(raw)


def get_allowed_content_types() -> set[str] | None:
    raw = os.environ.get('ALLOWED_UPLOAD_CONTENT_TYPES')
    if not raw:
        return None
    return {item.strip() for item in raw.split(',') if item.strip()}

def sanitize_filename(filename: str) -> str:
    name = filename.strip()
    if not name or name in ('.', '..') or '..' in name or '/' in name or '\\' in name:
        raise ValueError('Invalid filename')
    name = os.path.basename(name)

    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name)
    if not safe or safe in ('.', '..'):
        raise ValueError('Invalid filename')
    return safe
