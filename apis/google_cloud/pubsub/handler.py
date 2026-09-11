import json
import os

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1
from google_cloud.storage.handler import _get_credentials
from google_cloud.tasks.handler import tasks_defer

DEFAULT_TOPIC = 'file-upload-complete'
DEFAULT_SUBSCRIPTION = 'file-upload-complete-pull'

_publisher = None
_subscriber = None
_pull_future = None


def get_topic_name() -> str:
    return os.environ.get('PUBSUB_TOPIC', DEFAULT_TOPIC)


def get_subscription_name() -> str:
    return os.environ.get('PUBSUB_SUBSCRIPTION', DEFAULT_SUBSCRIPTION)


def _project_id() -> str:
    project = os.environ.get('GCP_PROJECT_ID')
    if project:
        return project
    return _get_credentials().project_id


def _publisher_client() -> pubsub_v1.PublisherClient:
    global _publisher
    if _publisher is None:
        credentials = _get_credentials()
        _publisher = pubsub_v1.PublisherClient(credentials=credentials)
    return _publisher


def _subscriber_client() -> pubsub_v1.SubscriberClient:
    global _subscriber
    if _subscriber is None:
        credentials = _get_credentials()
        _subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
    return _subscriber


def topic_path() -> str:
    publisher = _publisher_client()
    return publisher.topic_path(_project_id(), get_topic_name())


def subscription_path() -> str:
    subscriber = _subscriber_client()
    return subscriber.subscription_path(_project_id(), get_subscription_name())


def ensure_topic_and_pull_subscription() -> None:
    publisher = _publisher_client()
    path = topic_path()
    try:
        publisher.create_topic(request={'name': path})
    except AlreadyExists:
        pass

    subscriber = _subscriber_client()
    sub_path = subscription_path()
    try:
        subscriber.create_subscription(
            request={
                'name': sub_path,
                'topic': path,
                'ack_deadline_seconds': 600,
            }
        )
        return
    except AlreadyExists:
        pass

    try:
        existing = subscriber.get_subscription(request={'subscription': sub_path})
    except NotFound:
        return
    if existing.push_config.push_endpoint:
        subscriber.modify_push_config(
            request={
                'subscription': sub_path,
                'push_config': {},
            }
        )


def publish_file_upload_complete(payload: dict) -> str:
    body = json.dumps(payload).encode('utf-8')
    future = _publisher_client().publish(
        topic_path(),
        body,
        session_id=str(payload.get('session_id') or ''),
    )
    return future.result(timeout=30)


def start_pull_worker(on_payload) -> None:
    global _pull_future
    if _pull_future is not None:
        return

    def callback(message):
        def run():
            try:
                payload = json.loads(message.data.decode('utf-8'))
                on_payload(payload)
                message.ack()
            except Exception:
                message.nack()

        tasks_defer(run, delay_seconds=3)

    _pull_future = _subscriber_client().subscribe(
        subscription_path(),
        callback=callback,
    )
