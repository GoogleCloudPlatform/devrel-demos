from sentence_transformers import SentenceTransformer
from pyspark.sql import functions as F
from pyspark.sql import SparkSession
import pyspark.sql.types as T
import pandas as pd

PROJECT_ID = "ID"

spark = SparkSession.builder.getOrCreate()

model = SentenceTransformer("all-mpnet-base-v2")

@F.udf(returnType=T.ArrayType(T.FloatType()))
def transform(body) -> list:
    return model.encode(body).tolist()

bqpd_df = spark.read.format("bigquery").load("bigquery-public-data.breathe.nature")

embeddings = additions.withColumn("embeddings", transform("body"))
embeddings.write.format("bigquery").mode("append").save(f"{PROJECT_ID}.rag_data.embeddings")