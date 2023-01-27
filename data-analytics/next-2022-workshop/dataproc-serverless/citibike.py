# Copyright 2022 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License")
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https: // www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys

from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import BooleanType

if len(sys.argv) == 1:
    print("Please provide a dataset name.")

dataset = sys.argv[1]
table = "bigquery-public-data:new_york_citibike.citibike_trips"

spark = SparkSession.builder \
    .appName("pyspark-example") \
    .config("spark.jars", "gs://spark-lib/bigquery/spark-bigquery-with-dependencies_2.12-0.26.0.jar") \
    .getOrCreate()

df = spark.read.format("bigquery").load(table)

top_ten = df.filter(col("start_station_id")
                    .isNotNull()) \
            .groupBy("start_station_id") \
            .count() \
            .orderBy("count", ascending=False) \
            .limit(10) \
            .cache()

top_ten.show()

table = f"{dataset}.citibikes_top_ten_start_station_ids"
# Saving the data to BigQuery
top_ten.write.format('bigquery') \
  .option("writeMethod", "direct") \
  .option("table", table) \
  .save()

print(f"Data written to BigQuery table: {table}.citibikes_top_ten_start_station_ids")
