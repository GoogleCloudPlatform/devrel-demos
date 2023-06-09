import apache_beam as beam
import argparse
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions
from google.cloud import storage
import logging

class read_file(beam.DoFn):
    def process(self, element): 
        storage_client = storage.Client()
        bucket_name = element.split('/')[2]
        blob_name = "/".join(element.split('/')[3:])
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        # Check to see if readline would make difference
        with blob.open("r") as f:
            for data in f:
                yield data

def run(input_file,pipeline_args):
    pipeline_options = PipelineOptions(
        pipeline_args, save_main_session=True)
    my_options = pipeline_options.view_as(GoogleCloudOptions)
    #input_file = "gs://troubleshooting-in-beam/data/troubleshooting_data.csv"

    with beam.Pipeline(options=pipeline_options) as p:
        read_file_name = (
            p 
            | "Read from CSV" >> beam.Create([input_file]))

        file_data = read_file_name | beam.ParDo(read_file())
        count_records = (file_data | beam.combiners.Count.Globally().without_defaults())
        count_records | beam.Map(lambda element: logging.info(element))

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--input',
        dest='input_file',
        required=True,
        help=('location of data file'))
    known_args, pipeline_args = parser.parse_known_args()
    run(known_args.input_file,pipeline_args)