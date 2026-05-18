# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import os
from google.cloud import storage
from processor.csv_processor import process_csv
from processor.image_processor import process_image
from processor.video_processor import process_video
from processor.audio_processor import process_audio
from processor.bigquery_writer import write_graph_to_bq

def parse_gcs_path(gcs_path):
    """Converts gs://bucket/path to (bucket_name, blob_name)"""
    parts = gcs_path.replace("gs://", "").split("/", 1)
    return parts[0], parts[1]

def process_single_file(gcs_path: str):
    """
    Processes a single cloud resource file, extracts knowledge graph elements using 
    the appropriate AI processor, and delivers data to the active BigQuery instance.
    """
    print(f"\n🚀 Processing file: {gcs_path}")
    from google.genai.errors import ClientError

    # Verify existence for local/cloud uniformity
    # Verify existence for local/cloud uniformity natively
    client = storage.Client()
    if gcs_path.startswith("gs://"):
        try:
            bucket_name, blob_name = parse_gcs_path(gcs_path)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            if not blob.exists():
                print(f"❌ Error: File does not exist in GCS at: {gcs_path}")
                return False
        except Exception as e:
            print(f"❌ Error verifying GCS object: {e}")
            return False

    nodes, edges = [], []
    ext = os.path.splitext(gcs_path)[1].lower()
    
    try:
        match ext:
            case '.csv':
                if gcs_path.startswith("gs://"):
                    bucket_name, blob_name = parse_gcs_path(gcs_path)
                    bucket = client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    # Use python's string conversion directly without intermediate disk writes
                    content_as_string = blob.download_as_text()
                    from io import StringIO
                    nodes, edges = process_csv(StringIO(content_as_string))
                else:
                    with open(gcs_path, "r") as f:
                        nodes, edges = process_csv(f)
            case '.jpg' | '.jpeg' | '.png':
                nodes, edges = process_image(gcs_path)
            case '.mp4':
                nodes, edges = process_video(gcs_path)
            case '.wav':
                nodes, edges = process_audio(gcs_path)
            case _:
                print(f"⚠️  Skipping unsupported file type: {ext}")
                return False

    except ClientError as e:
        print(f"❌ Gemini API Client Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during processing: {e}")
        return False

    print(f"✅ Extraction complete. Found {len(nodes)} nodes and {len(edges)} edges.")
    if nodes or edges:
        write_graph_to_bq(nodes, edges)
    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python process_file.py gs://bucket/path/to/file")
        sys.exit(1)
    
    success = process_single_file(sys.argv[1])
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
