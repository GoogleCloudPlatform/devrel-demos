import sys
from pyspark.sql import SparkSession

project_id = sys.argv[1]
dataset_id = sys.argv[2]
table_name = "transactions"

spark = SparkSession.builder.appName("Dataplex Policy Enforcement Test").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

print(f"🔍 Reading {project_id}.{dataset_id}.{table_name} via BigQuery Storage API...")

# Reading data via Compute Delegation (Dataplex policies are applied dynamically here)
df = spark.read \
    .format("bigquery") \
    .option("table", f"{project_id}.{dataset_id}.{table_name}") \
    .load()

print("\n=== 📊 Data Preview ===")
df.show(truncate=False)