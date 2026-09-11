import os

from google.cloud import storage
from google.oauth2 import service_account

_client = None


def _get_credentials():
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        raise ValueError('GOOGLE_APPLICATION_CREDENTIALS environment variable is required')
    if not os.path.isfile(creds_path):
        raise ValueError(f'service account file not found: {creds_path}')
    return service_account.Credentials.from_service_account_file(creds_path)


def _get_client() -> storage.Client:
    global _client
    if _client is None:
        credentials = _get_credentials()
        _client = storage.Client(
            credentials=credentials,
            project=credentials.project_id,
        )
    return _client


def _get_bucket_name() -> str:
    bucket_name = os.environ.get('GCS_BUCKET_NAME')
    if not bucket_name:
        raise ValueError('GCS_BUCKET_NAME environment variable is required')
    return bucket_name


def create_resumable_upload_session(
    object_path: str,
    content_type: str,
    origin: str | None = None,
) -> str:
     
    client = _get_client()
    bucket = client.bucket(_get_bucket_name())
    blob = bucket.blob(object_path)
    return blob.create_resumable_upload_session(
        content_type=content_type,
        origin=origin,
    )


def _get_blob(object_path: str):
    client = _get_client()
    bucket = client.bucket(_get_bucket_name())
    return bucket.blob(object_path)


def blob_exists(object_path: str) -> bool:
    return _get_blob(object_path).exists()


def open_blob_text_stream(object_path: str):
    return _get_blob(object_path).open('rt', encoding='utf-8', errors='replace')
