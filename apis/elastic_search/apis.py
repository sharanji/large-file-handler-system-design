from elastic_search.client import search_chunks
from flask import request

from apis.common.auth.handler import auth

CONTENT_EXCERPT_CHARS = 280


def _content_excerpt(content: str) -> str:
    text = ' '.join((content or '').split())
    if len(text) <= CONTENT_EXCERPT_CHARS:
        return text
    return f'{text[:CONTENT_EXCERPT_CHARS].rstrip()}…'


@auth(auth_required=False)
def search_words():
    data = request.get_json(silent=True) or {}
    query = data.get('query') or request.args.get('query')
    session_id = data.get('session_id') or request.args.get('session_id')

    if not query or not isinstance(query, str) or not query.strip():
        return {'error': 'query is required'}, 400
    if session_id is not None and not isinstance(session_id, str):
        return {'error': 'session_id must be a string'}, 400

    try:
        result = search_chunks(query=query.strip(), session_id=session_id or None)
    except Exception:
        return {'error': 'Failed to search indexed files'}, 500

    hits = []
    for hit in result.get('hits', {}).get('hits', []):
        source = hit.get('_source') or {}
        highlights = hit.get('highlight', {}).get('content') or []
        snippets = highlights or [_content_excerpt(source.get('content') or '')]
        hits.append(
            {
                'filename': source.get('filename'),
                'session_id': source.get('session_id'),
                'chunk_index': source.get('chunk_index'),
                'line_start': source.get('line_start'),
                'line_end': source.get('line_end'),
                'snippets': snippets,
                'score': hit.get('_score'),
            }
        )

    total = result.get('hits', {}).get('total', {})
    if isinstance(total, dict):
        total_value = total.get('value', 0)
    else:
        total_value = total or 0

    return {'query': query.strip(), 'total': total_value, 'hits': hits}, 200
