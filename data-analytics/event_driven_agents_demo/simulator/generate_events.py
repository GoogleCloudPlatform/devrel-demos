# Copyright 2026 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Generates and streams synthetic transaction events to BigQuery."""

import json
import uuid
import random
import time
from datetime import datetime, timezone, timedelta
from google.cloud import bigquery

def create_bulk_events_file(filename="simulator/bulk_events.json", num_events=5000):
    """Generates a JSON file with thousands of background events and our injected anomaly."""
    events = []
    base_time = datetime.now(timezone.utc) - timedelta(hours=24)
    
    # Generate background noise
    countries = ["USA", "CAN", "MEX", "GBR", "FRA", "DEU", "JPN"]
    merchants = ["Coffee Shop", "Grocery Store", "Gas Station", "Online Retailer", "Restaurant"]
    
    print(f"Generating {num_events} background events...")
    for _ in range(num_events):
        event_time = base_time + timedelta(minutes=random.randint(0, 1400))
        events.append({
            "transaction_id": str(uuid.uuid4()),
            "transaction_time": event_time.isoformat(),
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "amount": round(random.uniform(5.0, 500.0), 2),
            "merchant_name": random.choice(merchants),
            "merchant_category_code": str(random.randint(5000, 5999)),
            "location_country": random.choice(countries),
            "is_international": random.choice([True, False]),
            "is_trusted_device": random.choice([True, False])
        })

    # --- INJECT IMPOSSIBLE TRAVEL FOR user_48503 ---
    # Transaction 1: Physical purchase in AUS
    time_one = datetime.now(timezone.utc) - timedelta(minutes=2)
    events.append({
        "transaction_id": str(uuid.uuid4()),
        "transaction_time": time_one.isoformat(),
        "user_id": "user_48503",
        "amount": 45.50,
        "merchant_name": "Sydney Cafe",
        "merchant_category_code": "5812",
        "location_country": "AUS",
        "is_international": False, 
        "is_trusted_device": True 
    })

    # Transaction 2: Physical purchase in GBR 2 minutes later (Triggers the Continuous Query)
    time_two = datetime.now(timezone.utc)
    events.append({
        "transaction_id": str(uuid.uuid4()),
        "transaction_time": time_two.isoformat(),
        "user_id": "user_48503",
        "amount": 2500.00,
        "merchant_name": "London Luxury Electronics",
        "merchant_category_code": "5732",
        "location_country": "GBR",
        "is_international": True,
        "is_trusted_device": False 
    })

    # Sort all events chronologically so the stream is realistic
    events.sort(key=lambda x: x["transaction_time"])

    with open(filename, 'w') as f:
        json.dump(events, f, indent=2)
        
    print(f"Successfully wrote {len(events)} events to {filename}")
    return filename

def stream_events_to_bigquery(filename):
    """Reads the JSON file and streams it to BigQuery in batches."""
    client = bigquery.Client()
    table_id = f"{client.project}.cymbal_bank.retail_transactions"
    
    with open(filename, 'r') as f:
        events = json.load(f)

    batch_size = 500
    print(f"Streaming {len(events)} events to {table_id} in batches of {batch_size}...")

    for i in range(0, len(events), batch_size):
        batch = events[i:i + batch_size]
        errors = client.insert_rows_json(table_id, batch)
        
        if errors:
            print(f"Encountered errors on batch {i // batch_size + 1}: {errors}")
        else:
            print(f"Successfully streamed batch {i // batch_size + 1}...")
            
        # Small sleep to avoid overwhelming the streaming API
        time.sleep(0.5)
        
    print("Finished streaming all events! The BigQuery continuous query should pick up the anomaly shortly.")

if __name__ == "__main__":
    # 1. Generate the JSON file
    json_file = create_bulk_events_file(filename="simulator/bulk_events.json", num_events=5000)
    
    # 2. Stream from the JSON file to BigQuery
    stream_events_to_bigquery(json_file)