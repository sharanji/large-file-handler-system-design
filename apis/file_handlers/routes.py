from .apis import initate_fileupload_session

apis = [
    ('/api/file-handler/create-session', initate_fileupload_session, ["POST"])
]