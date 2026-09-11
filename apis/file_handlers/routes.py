from .apis import complete_upload_session, create_upload_session, persist_upload_progress

apis = [
    ('/api/file-handler/create-upload-session', create_upload_session, ["POST"]),
    ('/api/file-handler/persist-upload-progress', persist_upload_progress, ["POST"]),
    ('/api/file-handler/complete-upload-session', complete_upload_session, ["POST"]),
]
