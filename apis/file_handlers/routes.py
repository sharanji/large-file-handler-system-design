from .apis import complete_upload_session, create_upload_session

apis = [
    ('/api/file-handler/create-upload-session', create_upload_session, ["POST"]),
    ('/api/file-handler/complete-upload-session', complete_upload_session, ["POST"]),
]
