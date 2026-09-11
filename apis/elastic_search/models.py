from dataclasses import asdict, dataclass
from enum import Enum


FILE_CHUNKS_INDEX = 'file_chunks'

FILE_CHUNKS_MAPPING = {
    'properties': {
        'session_id': {'type': 'keyword'},
        'object_path': {'type': 'keyword'},
        'filename': {'type': 'keyword'},
        'chunk_index': {'type': 'integer'},
        'line_start': {'type': 'integer'},
        'line_end': {'type': 'integer'},
        'content': {
            'type': 'text',
            'analyzer': 'standard',
            'term_vector': 'with_positions_offsets',
        },
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
