# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#import logging
import apache_beam as beam 
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.options.pipeline_options import SetupOptions
from apache_beam.ml.transforms.base import MLTransform
from apache_beam.ml.transforms.embeddings.vertex_ai import VertexAIImageEmbeddings
from apache_beam.ml.inference.base import RunInference
from apache_beam.ml.inference.vertex_ai_inference import VertexAIModelHandlerJSON
from apache_beam.io.jdbc import WriteToJdbc
from apache_beam.io import ReadFromPubSub
from apache_beam import coders
import typing
import tempfile
# Imports the Google Cloud client library
from google.cloud import storage

from google import genai
from google.genai import types
import base64
from vertexai.vision_models import Image
import argparse
from apache_beam.ml.inference.base import ModelHandler
from apache_beam.ml.inference.base import PredictionResult
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Optional
from typing import Sequence


def generate():
    client = genai.Client(
        vertexai=True,
        project="data-connect-demo6",
        location="us-central1",
    )


class GeminiModelHandler(ModelHandler):

    def load_model(self) -> genai.Client:
        """Loads and initializes a model for processing."""
        client = genai.Client(
            vertexai=True,
            project="data-connect-demo6",
            location="us-central1",
        )
        return client

    def run_inference(
        self,
        batch: Sequence[str],
        model: genai.Client,
        inference_args: Optional[Dict[str, Any]] = None
    ) -> Iterable[PredictionResult]:
        model_name = "gemini-2.0-flash-001"

        generate_content_config = types.GenerateContentConfig(
        temperature = 1,
        top_p = 0.95,
        max_output_tokens = 8192,
        response_modalities = ["TEXT"],
        )


        # Loop each text string, and use a tuple to store the inference results.
        predictions = []
        for one_text in batch:
            contents = [
                types.Content(
                    role="user",
                    parts=[
                    types.Part.from_text(text=one_text)
                    ]
                )
            ]
            result = ""
            for chunk in model.models.generate_content(
                model = model_name,
                contents = contents,
                config = generate_content_config,
                ):

                result = result + str(chunk)
            predictions.append((one_text,result))
        return predictions


project_id = "data-connect-demo6"
artifact_location = tempfile.mkdtemp(prefix='vertex_ai')

embedding_model_name = 'multimodalembedding@001'
mm_embedding_transform = VertexAIImageEmbeddings(
        model_name=embedding_model_name,
        # columns=['image','contextual_text'],
        columns=['image'],
        dimension=1408,
        project=project_id)

class EmbeddingRowSchema(typing.NamedTuple):
    image_path: str
    image_embedding: str

coders.registry.register_coder(EmbeddingRowSchema, coders.RowCoder)

class PrepImageFn(beam.DoFn):

    # def setup(self):

    def start_bundle(self):
        # Instantiates a client
        self.storage_client = storage.Client()
        #logging.info("GCS client initialized in start_bundle.")

    def process(self, element):
        #logging.info(f"Processing element: {element}")
        bucket = self.storage_client.get_bucket(element['image_bucket'])
        blob = bucket.get_blob(element['image_path_split'])
        blob_bytes = blob.download_as_bytes()
        image = Image(blob_bytes)
        element['image'] = image
        element['image_bytes'] = blob_bytes
        yield element

class DecodePubsubMessageFn(beam.DoFn):
    """Decodes Pub/Sub messages from JSON to Python dictionaries."""
    def process(self, element):
        """Decodes a single Pub/Sub message."""
        import json
        try:
            decoded_message = json.loads(element.decode('utf-8'))
            #logging.debug(f"Decoded Pub/Sub message: {decoded_message}")
            yield decoded_message
        except Exception as e:
            error_message = f"Error decoding message: {e}, message: {element.decode('utf-8')}"
            #logging.error(error_message)
            yield beam.pvalue.TaggedOutput('errors', element)

def run(argv=None, save_main_session=True):
    """Runs the pipeline"""

    parser = argparse.ArgumentParser()
    parser.add_argument('--alloydb_username',
                        dest='alloydb_username',
                        required=True,
                        help='AlloyDB username')
    parser.add_argument('--alloydb_password',
                        dest='alloydb_password',
                        required=True,
                        help='AlloyDB password')
    parser.add_argument('--alloydb_ip',
                        dest='alloydb_ip',
                        required=True,
                        help='AlloyDB IP Address')
    parser.add_argument('--alloydb_port',
                        dest='alloydb_port',
                        default="5432",
                        help='AlloyDB Port')
    parser.add_argument('--alloydb_database',
                        dest='alloydb_database',
                        required=True,
                        help='AlloyDB Database name')
    parser.add_argument('--alloydb_table',
                        dest='alloydb_table',
                        required=True,
                        help='AlloyDB table name')
    parser.add_argument('--pubsub_subscription', dest='pubsub_subscription', required=True)
    known_args, pipeline_args = parser.parse_known_args(argv)
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = save_main_session

    with beam.Pipeline(options=pipeline_options) as p:


        pubsub_pcoll = (
            p
            | "ReadFromPubSub" >> ReadFromPubSub(subscription=known_args.pubsub_subscription).with_output_types(bytes)
            | "DecodeMessage" >> beam.ParDo(DecodePubsubMessageFn())
        )
        pubsub_pcoll | "printPubsubstuff" >> beam.ParDo(lambda x: print(x))



        # Explain what a turnkey (MLTransform) is and why it is beneficial 
        embedding_pcoll = (
            pubsub_pcoll 
            | beam.ParDo(PrepImageFn()) 
            | "Embedding" >> MLTransform(write_artifact_location=artifact_location)
                .with_transform(mm_embedding_transform)
            | "ConvertToRows" >> beam.Map(
                lambda element: EmbeddingRowSchema(
                        image_path= element['image_path'], 
                        image_embedding= str(element['image'])
                ))
                .with_output_types(EmbeddingRowSchema)
        )

        # embedding_pcoll | "printMLTransformResults" >> beam.Map(lambda x: print(x))

        inference_pcoll = (pubsub_pcoll
            | "getText" >> beam.Map(lambda data: data['contextual_text'])
            | "performGeminiInf" >> RunInference(GeminiModelHandler())
            | "printText" >> beam.Map(lambda x: print(x))
        )

        embedding_pcoll | 'Write to jdbc' >> WriteToJdbc(
            driver_class_name='org.postgresql.Driver',
            table_name="image_embeddings",
            jdbc_url=(f'jdbc:postgresql://{known_args.alloydb_ip}:'
                        f'{known_args.alloydb_port}'
                        f'/postgres'),
            username=known_args.alloydb_username,
            password=known_args.alloydb_password,
            connection_properties='stringtype=unspecified'
        )

if __name__ == "__main__":
    run()