import os
import json
import random
import string
from google import genai
from google.genai.types import EmbedContentConfig
from langchain.text_splitter import RecursiveCharacterTextSplitter
from google.cloud import storage
from google.cloud import aiplatform

# Initialize GCP clients

# Cloud Storage
storage_client = storage.Client()

# Vertex AI Embeddings API (genai SDK)
os.environ["GOOGLE_CLOUD_PROJECT"] = os.getenv("PROJECT_ID")
os.environ["GOOGLE_CLOUD_LOCATION"] = os.getenv("GCP_REGION")
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
genai_client = genai.Client()  # Embeddings API

# Vertex AI Vector Search (fka Matching Engine)
project_id = os.getenv("PROJECT_ID")
location = os.getenv("GCP_REGION")
index_id = os.getenv("VECTOR_SEARCH_INDEX_ID")
index_endpoint_name = os.getenv("VECTOR_SEARCH_INDEX_ENDPOINT_NAME")
aiplatform_client = aiplatform.init(project=project_id, location=location)
index = aiplatform.MatchingEngineIndex(index_id)
index_endpoint = aiplatform.MatchingEngineIndexEndpoint(
    index_endpoint_name=index_endpoint_name
)


# ------- HELPER FUNCTIONS --------------------------
def randomStringDigits(stringLength=5):
    """Generate a random string of letters and digits"""
    lettersAndDigits = string.digits
    return "".join(random.choice(lettersAndDigits) for i in range(stringLength))


def gcs_download_document(bucket_name, blob_name):
    """
    Downloads raw text document from Cloud Storage bucket
    """
    print("🪣 Downloading doc from GCS:" + bucket_name + "/" + blob_name)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    dl = blob.download_as_string()
    # clean up the text
    return dl.decode("utf-8").strip().replace("\n", " ")


def chunk_text(text, chunk_size=500):
    """
    Chunks raw document text into roughly 500-character chunks, while preserving individual words. https://python.langchain.com/api_reference/text_splitters/character/langchain_text_splitters.character.RecursiveCharacterTextSplitter.html#recursivecharactertextsplitter

    Why 500? Another Vertex AI DB product, Vertex AI Search, uses a default chunk size of 500 tokens https://cloud.google.com/vertex-ai/generative-ai/docs/embeddings/get-text-embeddings#googlegenaisdk_embeddings_docretrieval_with_txt-python_genai_sdk
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size)
    return splitter.split_text(text)


def get_embeddings(text_chunks):
    """
    Call Vertex AI Embeddings API (text-embedding-005 model) to generate vector representations of all document chunks
    """
    to_write = []
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
        emb = response.embeddings[0].values
        body = {
            "id": randomStringDigits(stringLength=5),
            "text": chunk,
            "embedding": emb,
        }
        to_write.append(body)
    return to_write


def write_embeddings_to_jsonl(embeddings, outfile):
    """
    Write the embeddings to a JSONL file.
    JSONL ("JSON List") is what Vertex AI Vector Search needs for upsert.
    """
    print("📝 Writing embeddings to JSONL")
    with open(outfile, "w") as f:
        for embedding in embeddings:
            f.write(json.dumps(embedding) + "\n")


def store_embeddings_vavs(infile):
    """
    Upsert (stream) embeddings to Vertex AI Vector Search index.
    https://cloud.google.com/vertex-ai/docs/reference/rest/v1/projects.locations.indexes/upsertDatapoints#IndexDatapoint
    """
    with open(infile) as f:
        lines = f.readlines()
        datapoints = []
        for line in lines:
            item = json.loads(line)
            d = {
                "datapoint_id": str(item["id"]),
                # Correctly format the restricts field as a list of dictionaries
                "restricts": [{"namespace": "text", "allow_list": [item["text"]]}],
                "feature_vector": item["embedding"],
            }
            datapoints.append(d)

        print(
            "⬆️ Upserting "
            + str(len(datapoints))
            + " embeddings to Vertex AI Vector Search"
        )
        index.upsert_datapoints(datapoints=datapoints)
        print("✅ Done upserting.")


def extract_id_and_text(neighbor):
    """
    Extract ID and text from a Vertex AI Vector Search "MatchNeighbor" object
    """
    id_value = neighbor.id
    text_value = None
    if hasattr(neighbor, "restricts") and neighbor.restricts:
        for restrict in neighbor.restricts:
            if hasattr(restrict, "name") and restrict.name == "text":
                if hasattr(restrict, "allow_tokens") and restrict.allow_tokens:
                    text_value = restrict.allow_tokens[0]
                    break

    return {"id": id_value, "text": text_value}


def test_nearest_neighbors_query(q):
    """
    Test a query against the deployed Vertex AI Vector Search index.
    """
    response = genai_client.models.embed_content(
        model="text-embedding-005",
        contents=[q],
        config=EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=768,
        ),
    )
    query_embedding = response.embeddings[0].values
    print("Query is: " + str(q))
    neighbors = index_endpoint.find_neighbors(
        deployed_index_id=os.getenv("VECTOR_SEARCH_DEPLOYED_INDEX_ID"),
        queries=[query_embedding],
        num_neighbors=3,
        return_full_datapoint=True,  # Make sure this is True
    )

    print("Got # neighbors: " + str(len(neighbors[0])))
    for n in neighbors[0]:
        result = extract_id_and_text(n)
        print(f"ID: {result['id']}")
        print(f"Text: {result['text']}")


def ingest_text_document(filename):
    """
    Main ingestion function:
    - Downloads raw text from Cloud Storage
    - Chunks text
    - Generates embeddings
    - Writes embeddings to JSONL
    - Upserts embeddings as JSONL to Vertex AI Vector Search
    """
    gcs_bucket = os.getenv("GCS_BUCKET")
    filename = os.getenv("INPUT_DOC_FILENAME")
    raw_text = gcs_download_document(gcs_bucket, filename)
    print("\n📄 Raw text is char length: " + str(len(raw_text)))
    text_chunks = chunk_text(raw_text)
    print("\n✂️ Created " + str(len(text_chunks)) + " text chunks from document.")
    embeddings = get_embeddings(text_chunks)
    print("🧠 Created 1 embedding per chunk.")
    write_embeddings_to_jsonl(embeddings, "embeddings.json")
    store_embeddings_vavs("embeddings.json")
    test_nearest_neighbors_query("qubit")


if __name__ == "__main__":
    filename = os.getenv("INPUT_DOC_FILENAME")
    ingest_text_document(filename)
