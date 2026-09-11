from enum import Enum

GCS_BUCKET_NAME = 'txt_file_store'
GCP_PROJECT_ID = 'largefile-upload-design'
PUBSUB_TOPIC = 'file-upload-complete'
PUBSUB_SUBSCRIPTION = 'file-upload-complete-pull'
UPLOAD_SESSION_TTL_HOURS = 24
ALLOWED_UPLOAD_CONTENT_TYPES: set[str] | None = None


class UploadStates(str, Enum):
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_EXPIRED = 'expired'
