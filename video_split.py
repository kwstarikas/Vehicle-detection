import cv2
import os
import time
from confluent_kafka import Producer

# Kafka configuration
KAFKA_BROKER = "127.0.0.1:9092"
KAFKA_TOPIC = "video-chunks"


producer = Producer(
    {
        "bootstrap.servers": KAFKA_BROKER,
        "message.max.bytes": 50000000,  # Increase producer limit to match Kafka broker
        "batch.num.messages": 100,  # Adjust batch size
        "linger.ms": 100,  # Small delay to allow batching
    }
)


def delivery_report(err, msg):
    """Reports successful or failed delivery of a message."""
    if err:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")


def split_video_and_upload(video_path, chunk_duration=10):
    print("GOING TO SPLIT VIDEO AND UPLOAD CHUNKS ")
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print("Error: Could not open video file.")
        return

    fps = int(cap.get(cv2.CAP_PROP_FPS))  # Frames per second
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    chunk_size = fps * chunk_duration  # Frames per chunk

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # Codec for MP4

    chunk_counter = 1
    frame_counter = 0
    x = 3
    video_id = 0
    while frame_counter < total_frames:
        chunk_filename = f"chunk_{chunk_counter}.mp4"
        out = cv2.VideoWriter(chunk_filename, fourcc, fps, (frame_width, frame_height))

        for _ in range(chunk_size):
            ret, frame = cap.read()
            if not ret:
                break
            out.write(frame)
            frame_counter += 1

        out.release()  # Save the chunk
        print(f"Saved chunk: {chunk_filename}")

        # Read the chunk as bytes
        with open(chunk_filename, "rb") as f:
            chunk_data = f.read()

        # Produce the chunk to Kafka
        headers = [("chunk_no", str(chunk_counter))]
        producer.produce(
            topic=KAFKA_TOPIC,
            key=f"chunk_no_{chunk_counter}",
            value=chunk_data,
            headers=headers,
            callback=delivery_report,
        )
        print(f"Uploaded chunk {chunk_counter} to Kafka")
        producer.flush()

        # # Delete the chunk file after uploading
        # os.remove(chunk_filename)
        break
        if x == 3:
            break
        chunk_counter += 1

    cap.release()
    print("All chunks processed and uploaded.")


# Run the function
split_video_and_upload("test.mp4")


# produce_simple_message()
