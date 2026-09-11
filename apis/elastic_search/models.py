from dataclasses import asdict, dataclass
from enum import Enum


FILE_CHUNKS_INDEX = 'file_chunks_v2'

FILE_CHUNKS_SETTINGS = {
    'analysis': {
        'analyzer': {
            'chunk_text': {
                'type': 'english',
            }
        }
    }
}

CONTENT_TEXT_MAPPING = {
    'type': 'text',
    'analyzer': 'chunk_text',
    'term_vector': 'with_positions_offsets',
}

SEMANTIC_CONTENT_MAPPING = {
    'type': 'semantic_text',
}

FILE_CHUNKS_MAPPING = {
    'properties': {
        'session_id': {'type': 'keyword'},
        'object_path': {'type': 'keyword'},
        'filename': {'type': 'keyword'},
        'chunk_index': {'type': 'integer'},
        'line_start': {'type': 'integer'},
        'line_end': {'type': 'integer'},
        'content': {
            **CONTENT_TEXT_MAPPING,
            'copy_to': 'semantic_content',
        },
        'semantic_content': SEMANTIC_CONTENT_MAPPING,
    }
}

FILE_CHUNKS_MAPPING_LEXICAL = {
    'properties': {
        'session_id': {'type': 'keyword'},
        'object_path': {'type': 'keyword'},
        'filename': {'type': 'keyword'},
        'chunk_index': {'type': 'integer'},
        'line_start': {'type': 'integer'},
        'line_end': {'type': 'integer'},
        'content': CONTENT_TEXT_MAPPING,
    }
}


class IndexStatus(str, Enum):
    NOT_STARTED = 'not_started'
    INDEXING = 'indexing'
    INDEXED = 'indexed'
    FAILED = 'failed'


@dataclass
class FileChunkDocument:
    session_id: str
    object_path: str
    filename: str
    chunk_index: int
    line_start: int
    line_end: int
    content: str

    @property
    def document_id(self) -> str:
        return f'{self.session_id}:{self.chunk_index}'

    def to_es_body(self) -> dict:
        return asdict(self)
