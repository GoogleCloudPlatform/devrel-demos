import os
import json
from google import genai
from google.genai.types import EmbedContentConfig
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google.cloud import storage
from google.cloud import aiplatform

# Initialize GCP clients
os.environ["GOOGLE_CLOUD_PROJECT"] = "next25rag"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-central1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
storage_client = storage.Client()  # Cloud Storage
genai_client = genai.Client()  # Embbeddings API

# Vertex AI Vector Search
aiplatform_client = aiplatform.init(project="next25rag", location="us-central1")
index = aiplatform.MatchingEngineIndex("4890482584812781568")
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
    index_endpoint_name="projects/427092883710/locations/us-central1/indexEndpoints/5070556201163423744"
)


def gcs_download_document(bucket_name, blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    dl = blob.download_as_string()
    return dl.decode("utf-8").strip().replace("\n", " ")


# VAIS uses a default chunk size of 500 tokens https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings#googlegenaisdk_embeddings_docretrieval_with_txt-python_genai_sdk
# Source: https://python.langchain.com/api_reference/text_splitters/character/langchain_text_splitters.character.RecursiveCharacterTextSplitter.html#recursivecharactertextsplitter
def chunk_text(text, chunk_size=500):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size)
    return splitter.split_text(text)


def get_embeddings(text_chunks):
    to_write = []  # List to store embeddings
    for i, chunk in enumerate(text_chunks):
        print("⏲️ Generating embeddings for chunk " + str(i))
        response = genai_client.models.embed_content(
            model="text-embedding-005",
            contents=[chunk],
            config=EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=768,
            ),
        )
        emb = response.embeddings[0].values  # Extract the raw list of numerical values
        body = {"id": str(i), "text": chunk, "embedding": emb}
        to_write.append(body)
    return to_write


def write_embeddings_to_jsonl(embeddings, outfile):
    with open(outfile, "w") as f:
        for embedding in embeddings:
            print("📝 Writing embedding to JSONL")
            f.write(json.dumps(embedding) + "\n")


# https://stackoverflow.com/questions/79387866/how-to-add-metadata-to-an-index-datapoint-in-vertex-ai
# https://cloud.google.com/dotnet/docs/reference/Google.Cloud.AIPlatform.V1/latest/Google.Cloud.AIPlatform.V1.IndexDatapoint.Types.Restriction#properties
def store_embeddings_vavs(infile):
    with open(infile) as f:
        lines = f.readlines()

    datapoints = []
    for line in lines:
        item = json.loads(line)
        d = {
            "datapoint_id": str(item["id"]),
            "restricts": [{"namespace": "text", "allow_list": [item["text"]]}],
            "feature_vector": item["embedding"],
        }
        print(d)
        datapoints.append(d)

    print("⬆️ Upserting embeddings to Vertex AI Vector Search")
    index.upsert_datapoints(datapoints=datapoints)
    print("✅ Done.")


# https://cloud.google.com/vertex-ai/docs/vector-search/query-index-public-endpoint
def test_nearest_neighbors_query(emb_dict):
    query = "quantum computing"
    response = genai_client.models.embed_content(
        model="text-embedding-005",
        contents=[query],
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )
    query_embedding = response.embeddings[0].values

    neighbors = index_endpoint.find_neighbors(
        deployed_index_id="megan_text_index_endpoint2_1740675419602",
        queries=[query_embedding],
        num_neighbors=3,
    )
    print("Got # neighbors: " + str(len(neighbors[0])))
    for n in neighbors[0]:
        n_id = n.id  # Access the id attribute directly
        print(f"Neighbor ID: {n_id}, Distance: {n.distance}")
        print(f"Text: {emb_dict[n_id]}")


def ingest_text_document(filename):
    gcs_bucket = "ingest-67ab"
    raw_text = gcs_download_document(gcs_bucket, filename)
    print("\n📄 Raw text is char length: " + str(len(raw_text)))
    text_chunks = chunk_text(raw_text)
    print("\n✂️ Created " + str(len(text_chunks)) + " text chunks from document.")
    embeddings = get_embeddings(text_chunks)
    emb_dict = {}
    for emb in embeddings:
        emb_dict[emb["id"]] = emb["text"]
    print("🧠 Created 1 embedding per chunk.")
    write_embeddings_to_jsonl(embeddings, "embeddings.json")
    store_embeddings_vavs("embeddings.json")
    test_nearest_neighbors_query(emb_dict)


if __name__ == "__main__":
    filename = "willow_processor.txt"
    ingest_text_document(filename)
