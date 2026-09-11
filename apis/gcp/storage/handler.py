from google.cloud import storage

from gcp.auth import credentials_from_file

_clients: dict[str, storage.Client] = {}


def _client_key(credentials_path: str | None) -> str:
    return credentials_path or '_adc'


def get_client(credentials_path: str | None = None) -> storage.Client:
    key = _client_key(credentials_path)
    client = _clients.get(key)
    if client is None:
        credentials = credentials_from_file(credentials_path)
        if credentials is None:
            client = storage.Client()
        else:
            client = storage.Client(
                credentials=credentials,
                project=credentials.project_id,
            )
        _clients[key] = client
    return client


def get_blob(bucket_name: str, object_path: str, credentials_path: str | None = None):
    return get_client(credentials_path).bucket(bucket_name).blob(object_path)


def create_resumable_upload_session(
    bucket_name: str,
    object_path: str,
    content_type: str,
    credentials_path: str | None = None,
    origin: str | None = None,
) -> str:
    blob = get_blob(bucket_name, object_path, credentials_path)
    return blob.create_resumable_upload_session(
        content_type=content_type,
        origin=origin,
    )


def blob_exists(
    bucket_name: str,
    object_path: str,
    credentials_path: str | None = None,
) -> bool:
    return get_blob(bucket_name, object_path, credentials_path).exists()


def open_blob_text_stream(
    bucket_name: str,
    object_path: str,
    credentials_path: str | None = None,
    encoding: str = 'utf-8',
    errors: str = 'replace',
):
    return get_blob(bucket_name, object_path, credentials_path).open(
        'rt',
        encoding=encoding,
        errors=errors,
    )
