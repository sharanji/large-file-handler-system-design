from elastic_search.client import bulk_index_chunks
from elastic_search.models import FileChunkDocument
from google_cloud.storage.handler import open_blob_text_stream

LINES_PER_CHUNK = 200
BULK_BATCH_SIZE = 50


def index_uploaded_file(session_id: str, object_path: str, filename: str) -> int:
    chunks: list[FileChunkDocument] = []
    chunk_index = 0
    chunk_count = 0
    lines_buffer: list[str] = []
    line_start = 1
    current_line = 0

    def flush_buffer() -> None:
        nonlocal chunks, chunk_index, chunk_count, lines_buffer, line_start
        content = ''.join(lines_buffer)
        lines_buffer = []
        if not content.strip():
            return
        line_end = current_line
        chunks.append(
            FileChunkDocument(
                session_id=session_id,
                object_path=object_path,
                filename=filename,
                chunk_index=chunk_index,
                line_start=line_start,
                line_end=line_end,
                content=content,
            )
        )
        chunk_index += 1
        chunk_count += 1
        if len(chunks) >= BULK_BATCH_SIZE:
            bulk_index_chunks(chunks)
            chunks.clear()

    with open_blob_text_stream(object_path) as stream:
        for line in stream:
            if not lines_buffer:
                line_start = current_line + 1
            current_line += 1
            lines_buffer.append(line)
            if len(lines_buffer) >= LINES_PER_CHUNK:
                flush_buffer()
        if lines_buffer:
            flush_buffer()

    if chunks:
        bulk_index_chunks(chunks)

    return chunk_count
