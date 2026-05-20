#!/usr/bin/env python3
import argparse
import sys
import os
from google.cloud import storage
from google.cloud import pubsub_v1

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.mp4', '.wav', '.csv'}

def parse_gcs_uri(uri: str):
    """Extracts bucket name and prefix from a gs:// structure."""
    stripped = uri.replace("gs://", "")
    parts = stripped.split("/", 1)
    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""
    return bucket_name, prefix

def main():
    parser = argparse.ArgumentParser(description="Petverse Producer: Publishes GCS URIs to Pub/Sub.")
    parser.add_argument("uri", help="Root Target URI: e.g., gs://your-bucket-name/optional/folder/")
    parser.add_argument("--driver", help="Mandatory priority filename (e.g., pets.csv) forced to process first.", default=None)

    args = parser.parse_args()
    bucket_name, prefix = parse_gcs_uri(args.uri)

    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    topic_name = os.environ.get("PUBSUB_TOPIC", "petverse-topic")

    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT environment variable not set.")
        sys.exit(1)

    print(f"🔎 Initializing scanner on bucket: '{bucket_name}' @ prefix: '{prefix}'")
    storage_client = storage.Client()

    try:
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)
    except Exception as e:
        print(f"❌ Failed to access GCS bucket '{bucket_name}': {e}")
        sys.exit(1)

    discovery_list = []
    for b in blobs:
        if b.name.endswith("/"): # Skip explicit directory objects
            continue
        ext = os.path.splitext(b.name)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            discovery_list.append(b.name)

    if not discovery_list:
        print("⚠️  Bucket contains no manageable media files. Task completed.")
        return

    print(f"📦 Located {len(discovery_list)} target candidate files.")

    # User specific feature: Priority Queue positioning for "Driver" metadata files
    queue = []
    if args.driver:
        # Match exact matching filename in recursive path
        matches = [name for name in discovery_list if name.endswith(args.driver)]
        if matches:
            target_driver = matches[0]
            print(f"⭐ Found Driver file: {target_driver}. Promoting to priority 0.")
            queue.append(target_driver)
            # Remaining candidates sans the driver
            queue.extend([item for item in discovery_list if item != target_driver])
        else:
            print(f"⚠️  Specified driver '{args.driver}' not located in listing. Standard pipeline order preserved.")
            queue = discovery_list
    else:
         # Default: process ANY existing CSV first regardless of name, then media
         csvs = [i for i in discovery_list if i.endswith(".csv")]
         media = [i for i in discovery_list if not i.endswith(".csv")]
         queue = csvs + media

    print(f"🚀 Publishing {len(queue)} items to Pub/Sub topic '{topic_name}'...")

    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    success_count = 0
    fail_count = 0

    for item_name in queue:
        full_path = f"gs://{bucket_name}/{item_name}"
        try:
            future = publisher.publish(topic_path, data=full_path.encode("utf-8"))
            future.result() # Wait for publish to succeed
            print(f"✅ Published: {full_path}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to publish {full_path}: {e}")
            fail_count += 1

    print("\n" + "="*40)
    print(f"🏁 PRODUCER SUMMARY")
    print(f"✅ PUBLISHED : {success_count}")
    print(f"❌ FAILED    : {fail_count}")
    print("="*40)

    if fail_count > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
