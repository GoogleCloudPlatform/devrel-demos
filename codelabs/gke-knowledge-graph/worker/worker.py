#!/usr/bin/env python3
import os
import sys
import time
import socket
import logging
from google.cloud import pubsub_v1
from google.api_core.exceptions import DeadlineExceeded
from process_file import process_single_file

class LoggerWriter:
    def __init__(self, writer):
        self.writer = writer
        self.buf = ""

    def write(self, message):
        self.buf += message
        if "\n" in self.buf:
            parts = self.buf.split("\n")
            for part in parts[:-1]:
                if part.strip():
                    self.writer(part)
            self.buf = parts[-1]

    def flush(self):
        if self.buf.strip():
            self.writer(self.buf)
        self.buf = ""


def main():
    hostname = socket.gethostname()
    logging.basicConfig(
        level=logging.INFO,
        format=f'[{hostname}] %(asctime)s %(levelname)s %(message)s',
        stream=sys.stdout
    )
    sys.stdout = LoggerWriter(logging.info)
    sys.stderr = LoggerWriter(logging.error)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    subscription_name = os.environ.get("PUBSUB_SUBSCRIPTION", "petverse-sub")

    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set.")
        sys.exit(1)

    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(project_id, subscription_name)

    print(f"🚀 Worker starting. Polling subscription: {subscription_path}")

    idle_timeout = 60 # seconds
    last_message_time = time.time()

    while True:
        try:
            # Pull up to 1 message
            response = subscriber.pull(
                request={"subscription": subscription_path, "max_messages": 1},
                timeout=5.0 # Wait up to 5 seconds for a response
            )

            if response.received_messages:
                last_message_time = time.time() # Reset idle timer
                for msg in response.received_messages:
                    gcs_path = msg.message.data.decode("utf-8")
                    print(f"Received: {gcs_path}")

                    success = process_single_file(gcs_path)

                    if success:
                        subscriber.acknowledge(
                            request={
                                "subscription": subscription_path,
                                "ack_ids": [msg.ack_id],
                            }
                        )
                        print(f"✅ Acked: {gcs_path}")
                    else:
                        # Nack allows another worker to pick it up immediately
                        subscriber.modify_ack_deadline(
                            request={
                                "subscription": subscription_path,
                                "ack_ids": [msg.ack_id],
                                "ack_deadline_seconds": 0, # Make it available immediately
                            }
                        )
                        print(f"❌ Nacked (failed processing): {gcs_path}")
            else:
                # No messages received in this pull
                pass

        except DeadlineExceeded:
            # Expected if no messages are available within the 5s timeout
            pass
        except Exception as e:
            print(f"❌ Error during pull: {e}")
            time.sleep(5) # Avoid tight loop on error

        # Check idle timeout
        if time.time() - last_message_time > idle_timeout:
            print(f"⏱️ Idle timeout of {idle_timeout}s reached. Exiting.")
            break

    print("🏁 Worker shut down.")

if __name__ == "__main__":
    main()
