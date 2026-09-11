import os
import sys

sys.path.insert(0, 'apis/')

from common.env import load_app_env

load_app_env()

from common.db.connection import init_db
from common.routes import all_routes
from elastic_search.client import ensure_index
from file_handlers.apis import process_file_upload_complete_message
from file_handlers.constants import (
    GCP_PROJECT_ID,
    PUBSUB_SUBSCRIPTION,
    PUBSUB_TOPIC,
)
from flask import send_from_directory
from gcp.pubsub.handler import (
    ensure_pull_subscription,
    ensure_topic,
    start_pull_worker,
)

from app_factory import create_app

app = create_app()
init_db()
try:
    ensure_index()
except Exception:
    pass
try:
    project_id = GCP_PROJECT_ID
    topic = PUBSUB_TOPIC
    subscription = PUBSUB_SUBSCRIPTION
    credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    ensure_topic(topic, project_id, credentials_path)
    ensure_pull_subscription(
        subscription,
        topic,
        project_id,
        credentials_path,
        ack_deadline_seconds=600,
    )
    start_pull_worker(
        subscription,
        process_file_upload_complete_message,
        project_id,
        credentials_path,
    )
except Exception:
    pass


def configure_app_routes():
    for route in all_routes:
        api_url = route[0]
        handler = route[1]
        methods = route[2]
        app.add_url_rule(
            api_url,
            '{}|{}'.format(route, handler),
            handler,
            methods=methods,
        )


configure_app_routes()


@app.route('/hello')
def hello_world():
    return 'Server is running'


@app.route('/', methods=['GET'])
def index():
    return send_from_directory(app.static_folder, 'index.html')


if __name__ == '__main__':
    # app.run(host="0.0.0.0", port=8080)
    app.run(port=8091, debug=True)
