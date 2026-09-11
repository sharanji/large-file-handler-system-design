import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = './data/app.db'

_INDEX_COLUMNS = {
    'index_status': "TEXT NOT NULL DEFAULT 'not_started'",
    'indexed_at': 'TEXT',
    'index_error': 'TEXT',
    'chunk_count': 'INTEGER',
    'uploaded_bytes': 'INTEGER NOT NULL DEFAULT 0',
}


def get_db_path() -> str:
    return os.environ.get('SQLITE_DB_PATH', DEFAULT_DB_PATH)


def get_connection() -> sqlite3.Connection:
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS upload_sessions (
              id TEXT PRIMARY KEY,
              object_path TEXT NOT NULL,
              filename TEXT NOT NULL,
              content_type TEXT NOT NULL,
              size_bytes INTEGER,
              status TEXT NOT NULL,
              upload_url TEXT NOT NULL,
              created_at TEXT NOT NULL,
              expires_at TEXT NOT NULL,
              index_status TEXT NOT NULL DEFAULT 'not_started',
              indexed_at TEXT,
              index_error TEXT,
              chunk_count INTEGER
            )
            '''
        )
        existing = {
            row[1]
            for row in conn.execute('PRAGMA table_info(upload_sessions)').fetchall()
        }
        for column, definition in _INDEX_COLUMNS.items():
            if column not in existing:
                conn.execute(
                    f'ALTER TABLE upload_sessions ADD COLUMN {column} {definition}'
                )
        conn.commit()
    finally:
        conn.close()
