#  Copyright 2022 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import json
import logging
import typing

import apache_beam as beam
from apache_beam.transforms.external import ImplicitSchemaPayloadBuilder
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.transforms.sql import SqlTransform
from apache_beam.transforms.external import JavaExternalTransform

class ConvertToRow(beam.DoFn):
    def __init__(self, delimiter=","):
        self.delimiter = delimiter

    def process (self, element):
        line_array = element.split(self.delimiter)
        # Use beam.Row to create a schema-aware PCollection
        yield beam.Row(
            vendor_id=str(line_array[0]),
            pickup_datetime=str(line_array[1]),
            dropoff_datetime=str(line_array[2]),
            store_and_fwd_flag=str(line_array[3]),
            rate_code=str(line_array[4]),
            passenger_count=int(line_array[5]),
            trip_distance=float(line_array[6]),
            fare_amount=float(line_array[7]),
            extra=float(line_array[8]),
            mta_tax=float(line_array[9]),
            tip_amount=float(line_array[10]),
            tolls_amount=float(line_array[11]),
            ehail_fee=float(line_array[12] if line_array[12] != '' else 0),
            total_amount=float(line_array[13]),
            payment_type=str(line_array[14]),
            distance_between_service=float(line_array[15] if line_array[15] != '' else 0),
            time_between_service=int(line_array[16] if line_array[16] != '' else 0),
            trip_type=str(line_array[17]),
            imp_surcharge=float(line_array[18]),
            pickup_location_id=str(line_array[19]),
            dropoff_location_id=str(line_array[20])
        )

def run(input_files, pipeline_args):
    pipeline_options = PipelineOptions(
        pipeline_args, save_main_session=True)

    with beam.Pipeline(options=pipeline_options) as pipeline:
        sql_group_by = (
            pipeline
            | "Read the files" >> beam.io.textio.ReadFromText(input_files)
            | "Convert to Row" >> beam.ParDo(ConvertToRow(','))
            | SqlTransform(
                """
                 SELECT
                   rate_code,
                   COUNT(*) AS num_rides,
                   SUM(passenger_count) AS total_passengers,
                   SUM(trip_distance) AS total_distance,
                   SUM(fare_amount) as total_fare
                 FROM PCOLLECTION
                 GROUP BY rate_code"""))

        sql_group_by | beam.Map(lambda row: logging.info(row))

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input_files',
        dest='input_files',
        required=True,
        help=('input file pattern'))
    known_args, pipeline_args = parser.parse_known_args()

    run(known_args.input_files, pipeline_args)

