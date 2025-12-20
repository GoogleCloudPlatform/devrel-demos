import os
import glob
import time
from dotenv import load_dotenv
import vertexai
from vertexai.preview import rag
from google.cloud import storage
from google.api_core import exceptions

# --- Explicitly load the .env file from the v4 directory ---
dotenv_path = os.path.join(os.path.dirname(__file__), 'v4', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configuration ---
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
CORPUS_DISPLAY_NAME = "osquery_schema_corpus"
SCHEMA_FILES_GLOB = "./specs/**/*.txt" # Updated to .txt
BUCKET_NAME = f"{PROJECT_ID}-osquery-rag-schemas"

def setup_rag_corpus_with_gcs():
    """
    Creates a GCS bucket, uploads schema files, creates a Vertex AI RAG Corpus,
    and imports the files from GCS into the corpus.
    """
    if not PROJECT_ID or not LOCATION:
        print("Error: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION must be set.")
        return

    print(f"Initializing services for project '{PROJECT_ID}' in '{LOCATION}'...")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    storage_client = storage.Client(project=PROJECT_ID)

    # --- 1. Create GCS Bucket (if it doesn't exist) ---
    print(f"Checking for GCS Bucket: '{BUCKET_NAME}'...")
    try:
        bucket = storage_client.create_bucket(BUCKET_NAME, location=LOCATION)
        print(f"Bucket '{BUCKET_NAME}' created.")
    except exceptions.Conflict:
        print(f"Bucket '{BUCKET_NAME}' already exists.")
        bucket = storage_client.get_bucket(BUCKET_NAME)

    # --- 2. Clean and Upload Local Schema Files to GCS ---
    print("Deleting existing objects in GCS bucket for a clean upload...")
    for blob in bucket.list_blobs():
        blob.delete()
    
    print("Finding and uploading local .txt schema files to GCS...")
    file_paths = glob.glob(SCHEMA_FILES_GLOB, recursive=True)
    if not file_paths:
        print(f"Error: No .txt files found in '{os.path.abspath('./specs')}'.")
        return

    for file_path in file_paths:
        blob_name = os.path.relpath(file_path, './specs')
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(file_path)
    print(f"Uploaded {len(file_paths)} files to GCS.")

    # --- 3. Check for and/or Create the RAG Corpus ---
    print(f"Checking for RAG Corpus: '{CORPUS_DISPLAY_NAME}'...")
    corpora = rag.list_corpora()
    corpus = next((c for c in corpora if c.display_name == CORPUS_DISPLAY_NAME), None)

    if corpus:
        print(f"Corpus '{CORPUS_DISPLAY_NAME}' already exists (ID: {corpus.name}).")
    else:
        print("Corpus not found. Creating a new one...")
        try:
            corpus = rag.create_corpus(display_name=CORPUS_DISPLAY_NAME)
            print(f"Successfully created corpus. (ID: {corpus.name})")
        except Exception as e:
            print(f"Error creating RAG Corpus: {e}")
            return

    # --- 4. Validate Corpus before proceeding ---
    if not corpus or not corpus.name:
        print("Error: Failed to get a valid corpus object. Aborting import.")
        return

    # --- 5. Add a delay to ensure GCS consistency ---
    print("Waiting for 10 seconds to ensure GCS consistency before import...")
    time.sleep(10)

    # --- 6. Import Files from GCS into the RAG Corpus ---
    print("Starting import of files from GCS into the RAG Corpus...")
    gcs_uri = f"gs://{BUCKET_NAME}/"
    try:
        response = rag.import_files(
            corpus.name,
            [gcs_uri],
            chunk_size=1024
        )
        print(f"Successfully started file import job: {response}")
    except Exception as e:
        print(f"An error occurred during file import: {e}")
        return

    print("\n-----------------------------------------")
    print("✅ RAG setup initiated!")
    print(f"File upload and indexing from GCS has started for '{CORPUS_DISPLAY_NAME}'.")
    print("You can monitor the progress in the Google Cloud Console.")
    print(f"Corpus Name (for agent config): {corpus.name}")
    print("-----------------------------------------")

if __name__ == "__main__":
    setup_rag_corpus_with_gcs()
