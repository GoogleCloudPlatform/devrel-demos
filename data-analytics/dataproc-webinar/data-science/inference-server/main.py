import os
import json
import logging

from flask import Flask, request, jsonify
from google.cloud import storage
from pyspark.sql import SparkSession
from pyspark.ml import PipelineModel
from pyspark.sql.functions import hash, col, cast

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Download model
def download_model(bucket_name, source_blob_name, destination_dir):
    """
    Downloads a pre-trained Spark MLlib/ML PipelineModel.
    """
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=source_blob_name)
    
    for blob in blobs:
        if blob.name.endswith("/"):
            continue
        rel_path = os.path.relpath(blob.name, source_blob_name)
        dest_path = os.path.join(destination_dir, rel_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        blob.download_to_filename(dest_path)

# Load model
def load_model(model_path):
    """
    Loads a pre-trained Spark MLlib/ML PipelineModel.
    """
    try:
        return PipelineModel.load(model_path)
    except Exception as e:
        logging.error(f"Failed to load model: {e}")
        raise

# --- Initialization: Spark and Model Loading ---

GCS_BUCKET = os.environ.get("GCS_BUCKET")
GCS_MODEL_PATH = os.environ.get("GCS_MODEL_PATH")
LOCAL_MODEL_DIR = "/tmp/model"  
    
# Load Model on Startup
logging.info("Downloading model from GCS...")
download_model(GCS_BUCKET, GCS_MODEL_PATH, LOCAL_MODEL_DIR)
logging.info("Loading PySpark model...")
MODEL = load_model(LOCAL_MODEL_DIR)
logging.info("Model loaded.")

try:
    spark = SparkSession.builder \
        .appName("CloudRunSparkService") \
        .master("local[*]") \
        .getOrCreate()
    logging.info("Spark Session successfully initialized.")
except Exception as e:
    logging.error(f"Failed to initialize Spark Session: {e}")
    raise

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
