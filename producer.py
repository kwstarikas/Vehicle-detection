from confluent_kafka import Producer

KAFKA_BROKER = "127.0.0.1:9092"


conf = {
    "bootstrap.servers": KAFKA_BROKER,
}


def delivery_report(err, msg):
    """Reports successful or failed delivery of a message."""
    if err:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")


def produce_real_time_message(message, topic, key):

    producer = Producer(conf)
    producer.produce(
        topic=topic,
        key=key,
        value=message,
        callback=delivery_report,
    )
    producer.flush()
