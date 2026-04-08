import json
import random
import uuid
from datetime import datetime, timezone, timedelta

def generate_history():
    events = []
    now = datetime.now(timezone.utc)
    
    # 1. Target user (Karen Burton - USA)
    for _ in range(20):
        event_time = now - timedelta(days=random.uniform(0.1, 7.0))
        events.append({
            "transaction_id": str(uuid.uuid4()),
            "transaction_time": event_time.isoformat(),
            "user_id": "user_48503",
            "amount": round(random.uniform(15.0, 120.0), 2),
            "merchant_name": random.choice(["Target", "Whole Foods", "Starbucks", "Shell Gas"]),
            "merchant_category_code": "5411",
            "location_country": "USA",
            "is_international": False,
            "is_trusted_device": True
        })

    # 2. Background noise
    countries = ["USA", "CAN", "MEX", "GBR"]
    for _ in range(300):
        event_time = now - timedelta(days=random.uniform(0.1, 7.0))
        events.append({
            "transaction_id": str(uuid.uuid4()),
            "transaction_time": event_time.isoformat(),
            "user_id": f"user_{random.randint(10000, 99999)}",
            "amount": round(random.uniform(5.0, 300.0), 2),
            "merchant_name": "Generic Merchant",
            "merchant_category_code": str(random.randint(5000, 5999)),
            "location_country": random.choice(countries),
            "is_international": random.choice([True, False]),
            "is_trusted_device": random.choice([True, False])
        })

    # Sort chronologically
    events.sort(key=lambda x: x["transaction_time"])
    
    # Write to a local JSONL file
    with open("historical_events.json", "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")
            
    print("Successfully generated historical_events.json locally.")

if __name__ == "__main__":
    generate_history()