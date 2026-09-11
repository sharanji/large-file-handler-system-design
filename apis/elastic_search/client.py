import os
import ssl
from urllib.parse import urlparse, urlunparse

import certifi
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

from elasticsearch.exceptions import ApiError

from elastic_search.models import (
    FILE_CHUNKS_INDEX,
    FILE_CHUNKS_MAPPING,
    FILE_CHUNKS_MAPPING_LEXICAL,
    FILE_CHUNKS_SETTINGS,
    FileChunkDocument,
)

DEFAULT_ELASTICSEARCH_URL = 'http://localhost:9200'

_client = None


def get_elasticsearch_url() -> str:
    return os.environ.get('ELASTICSEARCH_URL', DEFAULT_ELASTICSEARCH_URL)


def _normalize_elastic_url(url: str) -> str:
    parsed = urlparse(url.strip())
    host = parsed.hostname or ''
    if not host:
        return url

    labels = host.split('.')
    if (
        host.endswith('.gcp.elastic-cloud.com')
        and '.es.' not in f'.{host}.'
        and len(labels) >= 5
        and labels[1] not in {'es', 'kb', 'apm', 'fleet'}
    ):
        labels.insert(1, 'es')
        host = '.'.join(labels)

    scheme = parsed.scheme or 'https'
    if 'elastic-cloud.com' in host:
        scheme = 'https'

    netloc = host
    if parsed.port:
        netloc = f'{host}:{parsed.port}'
    return urlunparse(
        (scheme, netloc, parsed.path or '', parsed.params, parsed.query, parsed.fragment)
    )


def _ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(cafile=certifi.where())
    return ctx


def _make_client() -> Elasticsearch:
    cloud_id = os.environ.get('ELASTIC_CLOUD_ID') or None
    api_key = os.environ.get('ELASTICSEARCH_API_KEY') or None
    username = os.environ.get('ELASTICSEARCH_USERNAME') or None
    password = os.environ.get('ELASTICSEARCH_PASSWORD') or None
    kwargs = {'request_timeout': 120}
    if api_key:
        kwargs['api_key'] = api_key
    elif username and password:
        kwargs['basic_auth'] = (username, password)
    if cloud_id:
        kwargs['ssl_context'] = _ssl_context()
        return Elasticsearch(cloud_id=cloud_id, **kwargs)

    url = _normalize_elastic_url(get_elasticsearch_url())
    if url.startswith('https://'):
        kwargs['ssl_context'] = _ssl_context()
    return Elasticsearch(url, **kwargs)


def get_client() -> Elasticsearch:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


def ensure_index() -> None:
    client = get_client()
    if client.indices.exists(index=FILE_CHUNKS_INDEX):
        return
    try:
        client.indices.create(
            index=FILE_CHUNKS_INDEX,
            settings=FILE_CHUNKS_SETTINGS,
            mappings=FILE_CHUNKS_MAPPING,
        )
    except ApiError:
        client.indices.create(
            index=FILE_CHUNKS_INDEX,
            settings=FILE_CHUNKS_SETTINGS,
            mappings=FILE_CHUNKS_MAPPING_LEXICAL,
        )


def bulk_index_chunks(chunks: list[FileChunkDocument]) -> None:
    if not chunks:
        return
    client = get_client()
    actions = [
        {
            '_index': FILE_CHUNKS_INDEX,
            '_id': chunk.document_id,
            '_source': chunk.to_es_body(),
        }
        for chunk in chunks
    ]
    bulk(client, actions)


def _session_filters(session_id: str | None) -> list[dict]:
    if session_id:
        return [{'term': {'session_id': session_id}}]
    return []


def _highlight() -> dict:
    return {
        'fields': {
            'content': {
                'number_of_fragments': 3,
                'fragment_size': 160,
            }
        }
    }


def _lexical_query(query: str, filters: list[dict]) -> dict:
    return {
        'bool': {
            'must': [
                {
                    'match': {
                        'content': {
                            'query': query,
                            'operator': 'or',
                            'fuzziness': 'AUTO',
                        }
                    }
                }
            ],
            'filter': filters,
        }
    }


def _semantic_query(query: str, filters: list[dict]) -> dict:
    return {
        'bool': {
            'must': [
                {
                    'semantic': {
                        'field': 'semantic_content',
                        'query': query,
                    }
                }
            ],
            'filter': filters,
        }
    }


def _hybrid_retriever(query: str, filters: list[dict]) -> dict:
    return {
        'rrf': {
            'retrievers': [
                {'standard': {'query': _lexical_query(query, filters)}},
                {'standard': {'query': _semantic_query(query, filters)}},
            ]
        }
    }


def search_chunks(query: str, session_id: str | None = None, size: int = 20) -> dict:
    filters = _session_filters(session_id)
    client = get_client()
    highlight = _highlight()
    try:
        return client.search(
            index=FILE_CHUNKS_INDEX,
            retriever=_hybrid_retriever(query, filters),
            highlight=highlight,
            size=size,
        )
    except ApiError:
        return client.search(
            index=FILE_CHUNKS_INDEX,
            query=_lexical_query(query, filters),
            highlight=highlight,
            size=size,
        )
