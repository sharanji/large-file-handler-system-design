import os

from google.oauth2 import service_account


def credentials_from_file(credentials_path: str | None):
    if not credentials_path:
        return None
    if not os.path.isfile(credentials_path):
        raise ValueError(f'service account file not found: {credentials_path}')
    return service_account.Credentials.from_service_account_file(credentials_path)
