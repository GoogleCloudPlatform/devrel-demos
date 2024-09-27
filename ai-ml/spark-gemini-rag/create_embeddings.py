from sentence_transformers import SentenceTransformer
from google.cloud import aiplatform
from pyspark.sql import functions as F
import pyspark.sql.types as T
import pandas as pd

df = spark.read.format("bigquery").load("bigquery-public-data.breathe.nature")
data = df.where(F.length("body") > 100).sample(.1).collect()