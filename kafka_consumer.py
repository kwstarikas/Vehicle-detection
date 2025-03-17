import cv2
import os
import time
from confluent_kafka import Consumer, KafkaError, KafkaException
import tempfile
import pprint
import threading

pp = pprint.PrettyPrinter(indent=4)

from detection import detect_vehicles

# Kafka configuration
KAFKA_BROKER = "127.0.0.1:9092"
KAFKA_TOPIC = "video-chunks"
CONSUMER_GROUP = "video-processor"

shutdown_event = threading.Event()


def create_consumer():
    """Create and configure a Kafka consumer."""
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",  # Start from the beginning if no offset is stored
            "enable.auto.commit": False,  # We'll manually commit offsets
            "max.partition.fetch.bytes": 52428800,  # 50MB to match producer's message size limit
        }
    )
    consumer.subscribe([KAFKA_TOPIC])
    return consumer


def process_video(video_path):
    """
    Process the reconstructed video file.
    Replace this with your actual video processing logic.
    """
    print(f"Processing video: {video_path}")
    # Example: Display basic information about the video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"Video Information:")
    print(f"- Resolution: {width}x{height}")
    print(f"- FPS: {fps}")
    print(f"- Duration: {duration:.2f} seconds")
    print(f"- Total frames: {frame_count}")

    cap.release()

    # Continue with your additional processing here
    # Your_function(video_path)


def consume_video_chunks():
    """Consume video chunks from Kafka and reconstruct the video."""
    consumer = create_consumer()

    try:
        # Dictionary to store chunks temporarily
        chunks = {}

        print("Starting to consume video chunks...")
        while True:
            print("I GO FIND MESSAGE")
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"Reached end of partition")
                else:
                    raise KafkaException(msg.error())
            else:
                # Get chunk number from headers
                chunk_no = None
                for header in msg.headers():
                    if header[0] == "chunk_no":
                        chunk_no = int(header[1])
                        break

                if chunk_no is None:
                    print("Warning: Received chunk without chunk number header")
                    continue

                # Save chunk to temporary file
                chunk_data = msg.value()
                chunks[chunk_no] = chunk_data
                print(f"Received chunk {chunk_no}, size: {len(chunk_data)} bytes")

                # Process chunks if we have all of them
                # Note: In a real system, you might want to implement a timeout mechanism
                if all(i in chunks for i in range(1, chunk_no + 1)):
                    print(f"All {chunk_no} chunks received. Reconstructing video...")

                    # Create a temporary file for the reconstructed video
                    with tempfile.NamedTemporaryFile(
                        suffix=".mp4", delete=False
                    ) as temp_file:
                        temp_path = temp_file.name

                    # Write chunks in order to the file
                    with open(temp_path, "wb") as f:
                        for i in range(1, chunk_no + 1):
                            f.write(chunks[i])

                    print(f"Video reconstructed at: {temp_path}")

                    # Process the reconstructed video
                    up, down = detect_vehicles(temp_path)
                    print("----- UP ------")
                    pp.pprint(up)
                    print("----- DOWN ------")
                    pp.pprint(down)

                    # Commit offsets after processing
                    consumer.commit(msg)

                    # Clear chunks dictionary
                    chunks.clear()

                    # Optional: break after processing one video
                    # Remove this if you want to continuously process videos
                    break

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Close the consumer
        consumer.close()
        shutdown_event.set()
        print("Consumer closed")
        return up, down


def alert_consumer():
    """Consumes messages from alert_topic for real-time alerts"""
    consumer = Consumer(
        {
            "bootstrap.servers": KAFKA_BROKER,
            "group.id": "real-time-alerts",
            "auto.offset.reset": "earliest",  # Start from the beginning if no offset is stored
            "enable.auto.commit": False,  # We'll manually commit offsets
        }
    )
    consumer.subscribe(["alerts"])

    try:
        while not shutdown_event.is_set():
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print(f"Consumer error: {msg.error()}")
                continue

            print(
                f"\n\n\n\n\n\n\n\n\n ----------------------Alert Consumer received: {msg.value().decode('utf-8')}"
            )

    except KafkaException as e:
        print(f"Kafka exception: {e}")
    finally:
        print("Closing alert consumer...")
        consumer.close()


alert_consumer_thread = threading.Thread(target=alert_consumer)
alert_consumer_thread.start()
up, down = consume_video_chunks()
alert_consumer_thread.join()
