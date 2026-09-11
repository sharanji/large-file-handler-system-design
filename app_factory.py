from flask import Flask
from flask_cors import CORS


def create_app():

    app = Flask(__name__, static_folder='assets', static_url_path='/assets')
    CORS(
        app,
        supports_credentials=True,
        resources={r'/*': {'origins': '*'}},
        allow_headers='*',
    )

    return app
