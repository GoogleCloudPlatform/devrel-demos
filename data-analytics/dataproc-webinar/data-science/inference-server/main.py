import os
import json
import logging

from flask import Flask, request, jsonify
from google.cloud import storage
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession
from pyspark.sql.functions import hash, col

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Initialization: Spark and Model Loading ---
GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_MODEL_PATH = os.environ.get("GCS_MODEL_PATH")
LOCAL_MODEL_PATH = "/tmp/model"

try:
    spark = SparkSession.builder \
        .appName("CloudRunSparkService") \
        .master("local[*]") \
        .getOrCreate()
    logging.info("Spark Session successfully initialized.")
except Exception as e:
    logging.error(f"Failed to initialize Spark Session: {e}")
    raise

def download_directory(bucket_name, prefix, local_path):
    """Downloads a directory from GCS to local filesystem."""
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    # Ensure prefix ends with '/' to avoid partial matches with other folders
    blobs = bucket.list_blobs(prefix=prefix)
    
    if len(blobs) == 0:
        logging.error(f"No files found in GCS bucket {bucket_name} at prefix {prefix}")
        return
    
    for blob in blobs:
        if blob.name.endswith("/"): continue # Skip directories
        
        # Structure local paths
        relative_path = os.path.relpath(blob.name, prefix)
        local_file_path = os.path.join(local_path, relative_path)
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        blob.download_to_filename(local_file_path)
    print(f"Model downloaded to {local_path}")

# Load model
def load_model(LOCAL_MODEL_PATH, GCS_BUCKET, GCS_MODEL_PATH):
    """Download and load model on startup to avoid latency per request."""
    global model
    if not os.path.exists(LOCAL_MODEL_PATH):
        download_directory(GCS_BUCKET, GCS_MODEL_PATH, LOCAL_MODEL_PATH)
    
    # Load the Spark ML model
    try:
        model = PipelineModel.load(LOCAL_MODEL_PATH)
        print("Spark model loaded successfully.")
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise
    
# Load Model on Startup
logging.info(f"Loading PySpark model from {GCS_MODEL_PATH}")
MODEL = load_model(LOCAL_MODEL_PATH, GCS_BUCKET, GCS_MODEL_PATH)
logging.info("Model loaded.")

# --- Flask Application Setup ---
app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    """
    Handles incoming POST requests for inference.
    Expects JSON data that can be converted into a Spark DataFrame.
    """
    if MODEL is None:
        return jsonify({"error": "Model failed to load at startup."}), 500

    try:
        # 1. Get data from the request
        data = request.get_json()
        
        # 2. Check length of list
        data_len = len(data)
        cap = 100
        if data_len > cap:
            return jsonify({"error": f"Too many records. Count: {data_len}, Max: {cap}"}), 400

        # 2. Create Spark DataFrame
        df = spark.createDataFrame(data)
        
        # 3. Transform data
        input_df = df.select(
            col("age").cast("DOUBLE").alias("age"), 
            (hash(col("country")).cast("BIGINT") * 1.0).alias("country_hash"),
            (hash(col("gender")).cast("BIGINT") * 1.0).alias("gender_hash"),
            (hash(col("traffic_source")).cast("BIGINT") * 1.0).alias("traffic_source_hash")
        )

        # 3. Perform Inference
        predictions_df = MODEL.transform(input_df)

        # 4. Prepare results (collect and serialize)
        results = [p.prediction for p in predictions_df.select("prediction").collect()]

        # 5. Return JSON response
        return jsonify({"predictions": results})

    except Exception as e:
        logging.error(f"An error occurred during prediction: {e}")
        #return jsonify({"error": str(e)}), 500
        raise e  
    
# Gunicorn entry point uses 'app' from this file
if __name__ == '__main__':
    # Local testing only: Cloud Run uses Gunicorn/CMD command
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
