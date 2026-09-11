import json

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import pubsub_v1

from gcp.auth import credentials_from_file

_publishers: dict[str, pubsub_v1.PublisherClient] = {}
_subscribers: dict[str, pubsub_v1.SubscriberClient] = {}
_pull_futures: dict[str, object] = {}


def _client_key(credentials_path: str | None) -> str:
    return credentials_path or '_adc'


def publisher_client(credentials_path: str | None = None) -> pubsub_v1.PublisherClient:
    key = _client_key(credentials_path)
    client = _publishers.get(key)
    if client is None:
        credentials = credentials_from_file(credentials_path)
        client = pubsub_v1.PublisherClient(credentials=credentials)
        _publishers[key] = client
    return client


def subscriber_client(credentials_path: str | None = None) -> pubsub_v1.SubscriberClient:
    key = _client_key(credentials_path)
    client = _subscribers.get(key)
    if client is None:
        credentials = credentials_from_file(credentials_path)
        client = pubsub_v1.SubscriberClient(credentials=credentials)
        _subscribers[key] = client
    return client


def topic_path(
    topic: str,
    project_id: str,
    credentials_path: str | None = None,
) -> str:
    return publisher_client(credentials_path).topic_path(project_id, topic)


def subscription_path(
    subscription: str,
    project_id: str,
    credentials_path: str | None = None,
) -> str:
    return subscriber_client(credentials_path).subscription_path(project_id, subscription)


def ensure_topic(
    topic: str,
    project_id: str,
    credentials_path: str | None = None,
) -> str:
    publisher = publisher_client(credentials_path)
    path = topic_path(topic, project_id, credentials_path)
    try:
        publisher.create_topic(request={'name': path})
    except AlreadyExists:
        pass
    return path


def ensure_pull_subscription(
    subscription: str,
    topic: str,
    project_id: str,
    credentials_path: str | None,
    ack_deadline_seconds: int,
) -> str:
    subscriber = subscriber_client(credentials_path)
    sub_path = subscription_path(subscription, project_id, credentials_path)
    topic_resource = topic_path(topic, project_id, credentials_path)
    try:
        subscriber.create_subscription(
            request={
                'name': sub_path,
                'topic': topic_resource,
                'ack_deadline_seconds': ack_deadline_seconds,
            }
        )
        return sub_path
    except AlreadyExists:
        pass

    try:
        existing = subscriber.get_subscription(request={'subscription': sub_path})
    except NotFound:
        return sub_path
    if existing.push_config.push_endpoint:
        subscriber.modify_push_config(
            request={
                'subscription': sub_path,
                'push_config': {},
            }
        )
    return sub_path


def publish(
    topic: str,
    payload: dict,
    project_id: str,
    credentials_path: str | None = None,
    attributes: dict[str, str] | None = None,
) -> str:
    body = json.dumps(payload).encode('utf-8')
    future = publisher_client(credentials_path).publish(
        topic_path(topic, project_id, credentials_path),
        body,
        **(attributes or {}),
    )
    return future.result()


def start_pull_worker(
    subscription: str,
    on_payload,
    project_id: str,
    credentials_path: str | None = None,
) -> None:
    path = subscription_path(subscription, project_id, credentials_path)
    if path in _pull_futures:
        return

    def callback(message):
        try:
            payload = json.loads(message.data.decode('utf-8'))
            on_payload(payload)
            message.ack()
        except Exception:
            message.nack()

    _pull_futures[path] = subscriber_client(credentials_path).subscribe(
        path,
        callback=callback,
    )
