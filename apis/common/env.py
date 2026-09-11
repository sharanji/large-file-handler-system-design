import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f'{name} environment variable is required')
    return value


def load_app_env() -> None:
    load_dotenv(PROJECT_ROOT / '.env', override=True)
    creds = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds:
        return
    path = Path(creds)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(path.resolve())


load_app_env()
