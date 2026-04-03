import os
import json
from google.cloud import bigquery

def export_data():
    project_id = os.environ.get("PROJECT_ID")
    if not project_id:
        print("Error: PROJECT_ID environment variable not set. Please run 'export PROJECT_ID=$(gcloud config get-value project)'")
        return

    print(f"Connecting to BigQuery in project: {project_id}...")
    client = bigquery.Client(project=project_id)
    
    query = """
    SELECT 
      m.auction_id as id,
      m.predicted_market_value,
      m.price_score,
      m.condition as condition_score,
      m.authenticity_score as scam_distance,
      CAST(m.deal_score AS INT64) as deal_score,
      v.description,
      m.description_summary
    FROM `model_dev.marketplace_listings` m
    JOIN `model_dev.vehicle_metadata` v ON m.auction_id = v.auction_id
    """
    
    try:
        query_job = client.query(query)
        results = query_job.result()
        
        # Build dictionary of new AI scores from BigQuery
        updates = {}
        for row in results:
            updates[row['id']] = {
                'predicted_market_value': row['predicted_market_value'],
                'price_score': row['price_score'],
                'condition_score': row['condition_score'],
                'scam_distance': row['scam_distance'],
                'deal_score': row['deal_score'],
                'raw_html_description': row['description'],
                'short_description': row['description_summary']
            }
            
        # Path to the static frontend payload
        output_path = os.path.join(os.path.dirname(__file__), '../../app/src/data/cars.json')
        
        with open(output_path, 'r') as f:
            cars_data = json.load(f)
            
        updated_count = 0
        for car in cars_data:
            car_id = str(car['id'])
            
            # Remap image URLs to the user's specific bucket
            if 'preview_image' in car:
                car['preview_image'] = car['preview_image'].replace('sample-data-and-media', f'cymbal-autos-{project_id}')
            if 'all_images' in car:
                car['all_images'] = [img.replace('sample-data-and-media', f'cymbal-autos-{project_id}') for img in car['all_images']]
                
            if car_id in updates:
                car.update(updates[car_id])
                updated_count += 1
                
        # Re-sort the master payload so the best deals appear first in the grid
        cars_data.sort(key=lambda x: x.get('deal_score', 0), reverse=True)
        
        with open(output_path, 'w') as f:
            json.dump(cars_data, f, indent=2)
            
        print(f"✅ Successfully synced {updated_count} listings with new BigQuery AI scores!")
        print(f"💾 Updated local file: app/src/data/cars.json")
        
    except Exception as e:
        print(f"Error querying BigQuery or writing data: {e}")

if __name__ == "__main__":
    export_data()
