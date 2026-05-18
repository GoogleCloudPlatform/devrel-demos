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

import json
import os
from processor.csv_processor import process_csv
from processor.image_processor import process_image
from processor.audio_processor import process_audio
from processor.video_processor import process_video

# 1. Test CSV Processor
print("\n🧪 1. Testing CSV Processor...")
try:
    with open('/tmp/pets.csv', 'r') as f:
        nodes, edges = process_csv(f)
        print(f"✅ Success! Extracted {len(nodes)} nodes and {len(edges)} edges.")
        if nodes:
            print("Sample Node:", nodes[0])
except Exception as e:
    print("❌ CSV Processor Error:", e)

# 2. Test Image Processor (Requires Working Gemini Credentials)
print("\n🧪 2. Testing Image Processor...")
try:
    gcs_image = "gs://sample-data-and-media/petverse/Joel_Profile_Picture.jpg"
    nodes, edges = process_image(gcs_image)
    print(f"✅ Success! Extracted {len(nodes)} nodes and {len(edges)} edges from {gcs_image}")
    if nodes:
        print("Sample Node:", nodes[0])
except Exception as e:
    print("❌ Image Processor Error:", e)

# 3. Test Audio Processor
print("\n🧪 3. Testing Audio Processor...")
try:
    gcs_audio = "gs://sample-data-and-media/petverse/additional_media/pixel_description.wav"
    nodes, edges = process_audio(gcs_audio)
    print(f"✅ Success! Extracted {len(nodes)} nodes and {len(edges)} edges from {gcs_audio}")
    if nodes:
        print("Sample Node:", nodes[0])
except Exception as e:
    print("❌ Audio Processor Error:", e)

