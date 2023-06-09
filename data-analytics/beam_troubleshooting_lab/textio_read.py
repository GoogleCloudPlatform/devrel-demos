import apache_beam as beam
import argparse
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions
import logging

def run(input_file,pipeline_args):
    pipeline_options = PipelineOptions(
        pipeline_args, save_main_session=True)
    my_options = pipeline_options.view_as(GoogleCloudOptions)
    #input_file = "gs://troubleshooting-in-beam/data/troubleshooting_data.csv"

    with beam.Pipeline(options=pipeline_options) as p:
        read_file = (
            p 
            | "Read from CSV" >> beam.io.ReadFromText(input_file))
        
        _ = (
            read_file
            | beam.combiners.Count.Globally()
            | beam.Map(lambda element: logging.info(element)))

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