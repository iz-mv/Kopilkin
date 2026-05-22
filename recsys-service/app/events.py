import json
import os
from datetime import datetime
from typing import Any, Dict

from kafka import KafkaProducer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092"
)

_producer = None


def get_producer():
    global _producer

    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
            key_serializer=lambda key: key.encode("utf-8") if key else None,
        )

    return _producer


def publish_event(topic: str, key: str, event: Dict[str, Any]) -> None:
    event["published_at"] = datetime.utcnow().isoformat()

    try:
        producer = get_producer()
        producer.send(topic, key=key, value=event)
        producer.flush()
        print(f"[Kafka] Published event to topic={topic}, key={key}")
    except Exception as error:
        print(f"[Kafka] Failed to publish event to topic={topic}: {error}")