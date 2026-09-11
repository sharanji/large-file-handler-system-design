import os
import re


def sanitize_filename(filename: str) -> str:
    name = filename.strip()
    if not name or name in ('.', '..') or '..' in name or '/' in name or '\\' in name:
        raise ValueError('Invalid filename')
    name = os.path.basename(name)

    safe = re.sub(r'[^A-Za-z0-9._-]+', '_', name)
    if not safe or safe in ('.', '..'):
        raise ValueError('Invalid filename')
    return safe
