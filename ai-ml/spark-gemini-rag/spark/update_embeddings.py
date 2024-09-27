from sentence_transformers import SentenceTransformer
from pyspark.sql import functions as F
from pyspark.sql import SparkSession
import pyspark.sql.types as T
import pandas as pd

PROJECT_ID = "YOUR_PROJECT_ID"

spark = SparkSession.builder.getOrCreate()

model = SentenceTransformer("all-mpnet-base-v2")

@F.udf(returnType=T.ArrayType(T.FloatType()))
def transform(body) -> list:
    return model.encode(body).tolist()

bqpd_df = spark.read.format("bigquery").load("bigquery-public-data.breathe.nature")
emb_df = spark.read.format("bigquery").load(f"{PROJECT_ID}.rag_data.embeddings")

new_ids = bqpd_df.select("id").subtract(emb_df.select("id"))

if new_ids.count() > 0:
    additions = new_ids.join(bqpd_df, on="id")
    new_embeddings = additions.withColumn("embeddings", transform("body"))
    new_embeddings.write.format("bigquery").mode("append").save(f"{PROJECT_ID}-hackathon.rag_data.embeddings")