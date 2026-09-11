import os
from enum import Enum

DEFAULT_UPLOAD_SESSION_TTL_HOURS = 24
class UploadStates(str, Enum):
    STATUS_PENDING = 'pending'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_EXPIRED = 'expired'

