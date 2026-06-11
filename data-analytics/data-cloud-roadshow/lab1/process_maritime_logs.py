# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
     

import sys
import os
import random
import hashlib
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import ArrayType, FloatType

def process_log_text(log_path: str):
    """
    Reads unstructured text from GCS by splitting it into individual sentences and 
    generating a simulated embedding vector for each.
    """
    # Reads full text file into a dataframe with a default column named 'value'
    raw_df = spark.read.text(log_path)
    
    # Step 1: Define extraction regex conforming to our messy generator layout
    # Pattern grabs: [Timestamp], ignores severity, {custodian_id:ID}, leaves :: Message
    log_pattern = r"^\[(.*?)\]\s+--\s+\w+\s+--\s+\{custodian_id:(.*?)\}\s+::\s+(.*)$"

    # Step 2: Perform struct normalization using PySpark DSL regex methods
    extracted_df = raw_df.select(
        F.regexp_extract(F.col("value"), log_pattern, 1).alias("log_timestamp"),
        F.regexp_extract(F.col("value"), log_pattern, 2).alias("custodian_id"),
        F.regexp_extract(F.col("value"), log_pattern, 3).alias("raw_message")
    )

    # Step 3: Explode the message column into discrete sentences while retaining parent metadata & raw context
    sentence_df = extracted_df.select(
        F.col("log_timestamp"),
        F.col("custodian_id"),
        F.col("raw_message"),
        F.explode(F.split(F.col("raw_message"), r"(?<=[.!?])\s+")).alias("sentence")
    ).filter(F.col("sentence") != "")

    # Simulated embedding generation function (UDF)
    def simulate_embedding(text):
        if not text:
            return []
        # Generate a stable integer seed using a hash of the exact text snippet.
        # Prevents cross-thread mutation side effects that global random.seed caused.
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        local_rng = random.Random(seed)
        return [float(local_rng.random()) for _ in range(5)]

    embedding_udf = F.udf(simulate_embedding, ArrayType(FloatType()))
    
    # Append the simulated embeddings to dataframe
    final_df = sentence_df.withColumn("embedding_vector", embedding_udf(F.col("sentence")))
    
    return final_df

####################------DELETE------##############################
# ARGHH!!!! Don't think this code will run so easily. I'll stop you!
print("PYTHON PIRATES STRIKE AGAIN!!!!!")
sys.exit(1) # This might be the reason...
####################------DELETE------##############################

# Read from explicit centralized GCS resource
BUCKET_NAME = sys.argv[1]
input_gcs_path = f"gs://{BUCKET_NAME}/raw_logs/maritime_logs.txt"

spark = SparkSession.builder \
    .appName("LostCargoLogsProcessor") \
    .getOrCreate()

print(f"Processing Unstructured Logs from GCS source: {input_gcs_path}")
processed_results = process_log_text(input_gcs_path)

spark.sql("USE lost_cargo_namespace;")

spark.sql("""CREATE TABLE IF NOT EXISTS processed_maritime_logs (
    log_timestamp    STRING,
    custodian_id     STRING,
    raw_message      STRING,
    sentence         STRING,
    embedding_vector ARRAY<FLOAT>
) 
USING iceberg;""")

processed_results.write \
  .format("iceberg") \
  .mode("append") \
  .save("processed_maritime_logs")
