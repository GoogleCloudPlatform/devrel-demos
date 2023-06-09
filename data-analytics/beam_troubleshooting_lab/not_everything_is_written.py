import apache_beam as beam
import argparse
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import GoogleCloudOptions
import logging

class count_words(beam.DoFn):
    def process(self, element):
        split_word = element.split(" ")
        yield ({"data_col" : "Count is : {}".format(len(split_word))})
        yield ({"data_col" : "Original data was : ".format(element)})
        
def run(pipeline_args):
    pipeline_options = PipelineOptions(
        pipeline_args, save_main_session=True)
    my_options = pipeline_options.view_as(GoogleCloudOptions)
    input_topic = "projects/{}/topics/input_topic_for_demo".format(my_options.project)
    with beam.Pipeline(options=pipeline_options) as p:
        read_line = (
            p 
            | "Read from PubSub" >> beam.io.ReadFromPubSub(topic=input_topic)
            | "Convert to string" >> beam.Map(lambda element: element.decode('UTF-8')))
        
        data_to_write = read_line | beam.ParDo(count_words())

        data_schema = {'fields': [
            {'name': 'data_col', 'type': 'STRING', 'mode': 'NULLABLE'}]}

        _ = (data_to_write
            | beam.io.gcp.bigquery.WriteToBigQuery(
                table=lambda element: "{}:demo.word_counts".format(my_options.project) if "Count" in element else "{}:demo.original_data".format(my_options.project),
                create_disposition="CREATE_NEVER",
                method=beam.io.gcp.bigquery.WriteToBigQuery.Method.STREAMING_INSERTS,
                schema = data_schema ))

if __name__ == "__main__":
    logging.getLogger().setLevel(logging.INFO)
    parser = argparse.ArgumentParser()
    known_args, pipeline_args = parser.parse_known_args()
    run(pipeline_args)