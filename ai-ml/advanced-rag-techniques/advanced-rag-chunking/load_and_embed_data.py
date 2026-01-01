import os
import uuid
import json
import pg8000 # type: ignore
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
from langchain_core.documents import Document
from langchain_community.vectorstores.pgvector import PGVector, DistanceStrategy
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_text_splitters import (
    CharacterTextSplitter,
    RecursiveCharacterTextSplitter,
    TokenTextSplitter
)
import traceback
import logging
import google.cloud.logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv() 

# Global constants for chunking (can be modified by user as per interactive steps)
MAX_DOCS_TO_PROCESS = 2 
CHUNK_SIZE = 250
CHUNK_OVERLAP = 50

def _get_env_vars():
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION")
    sql_instance_name = os.getenv("SQL_INSTANCE_NAME")
    db_instance_connection_name = f"{project_id}:{region}:{sql_instance_name}"

    env_vars = {
        "project_id": project_id,
        "region": region,
        "sql_instance_name": sql_instance_name,
        "db_name": os.getenv("SQL_DATABASE_NAME"),
        "db_user": os.getenv("SQL_USER"),
        "db_pass": os.getenv("SQL_PASSWORD"),
        "pgvector_base_collection_name": os.getenv("PGVECTOR_BASE_COLLECTION_NAME"),
        "books_json_gcs_path": os.getenv("BOOKS_JSON_GCS_PATH"),
        "db_instance_connection_name": db_instance_connection_name

    }
    if not all(env_vars.values()):
        missing_vars = [key for key, value in env_vars.items() if not value]
        print(f"Error: Missing environment variables: {', '.join(missing_vars)}")
        print("Please ensure all required environment variables are set.")
        return None
    return env_vars

def _init_connector_and_engine(env_vars):
    print("Initializing Cloud SQL Python Connector...")
    connector = Connector()
    def getconn() -> pg8000.dbapi.Connection:
        conn = connector.connect(
            env_vars["db_instance_connection_name"],
            "pg8000",
            user=env_vars["db_user"],
            password=env_vars["db_pass"],
            db=env_vars["db_name"],
            ip_type=IPTypes.PUBLIC,
            enable_iam_auth=False
        )
        return conn
    print(f"Creating SQLAlchemy engine for Cloud SQL instance: {env_vars['db_instance_connection_name']} (for PGVector connection handling)...")
    db_engine = sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
    return connector, db_engine, getconn

def _download_and_parse_json(gcs_path):
    # Using a unique local path to avoid conflicts if lab is run multiple times quickly
    local_json_path = f"./harry_potter_books_downloaded_{str(uuid.uuid4())[:8]}.json"
    print(f"Attempting to download '{gcs_path}' to '{local_json_path}' using gcloud...")
    gcloud_command = f"gcloud storage cp \"{gcs_path}\" \"{local_json_path}\""
    return_code = os.system(gcloud_command)
    if return_code != 0:
        print(f"Error downloading JSON file using gcloud. gcloud exited with code {return_code}.")
        if os.path.exists(local_json_path): os.remove(local_json_path)
        raise Exception(f"Failed to download JSON file. Return code: {return_code}")
    if not os.path.exists(local_json_path):
        raise FileNotFoundError(f"Downloaded JSON file not found locally at {local_json_path}")
    print(f"Successfully downloaded to '{local_json_path}'. Loading JSON data...")
    with open(local_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    try:
        os.remove(local_json_path)
        print(f"Cleaned up downloaded file: {local_json_path}")
    except OSError as e_remove:
        print(f"Warning: Could not clean up downloaded file {local_json_path}: {e_remove}")
    return data

def _prepare_and_chunk_documents(data_items, strategy, max_docs, chunk_size, chunk_overlap):
    print(f"Preparing and chunking documents with strategy: {strategy}, max_docs: {max_docs}, chunk_size: {chunk_size}, overlap: {chunk_overlap}")
    initial_documents = []
    for item in data_items:
        if "kwargs" in item and "page_content" in item["kwargs"]:
            page_content = item["kwargs"]["page_content"]
            metadata = item["kwargs"].get("metadata", {})
            if not isinstance(metadata, dict):
                metadata = {"original_metadata": str(metadata)} # Ensure metadata is a dict
            initial_documents.append(Document(page_content=page_content, metadata=metadata))
        else:
            print(f"Skipping item due to missing 'kwargs' or 'page_content': {str(item)[:100]}...")
    
    if not initial_documents:
        print("No initial documents were processed from the JSON file.")
        return []

    if len(initial_documents) > max_docs:
        print(f"INFO: Processing only the first {max_docs} initial documents out of {len(initial_documents)} before chunking.")
        initial_documents = initial_documents[:max_docs]
    else:
        print(f"Processing all {len(initial_documents)} initial documents as it's within MAX_DOCS_TO_PROCESS limit of {max_docs}.")

    if strategy == "character":
        splitter = CharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif strategy == "recursive":
        splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    elif strategy == "token":
        # Note: TokenTextSplitter by default uses gpt2 tokenizer (tiktoken)
        # For Gemini models, a different tokenizer might be more aligned if strict token counting is critical.
        # However, for general chunking, this is acceptable for demonstration.
        splitter = TokenTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    else:
        raise ValueError(f"Unknown chunking strategy: {strategy}")
    
    chunked_documents = splitter.split_documents(initial_documents)
    
    final_docs_with_ids = []
    for chunk_doc in chunked_documents:
        # Ensure metadata is a dict, even if empty, for PGVector compatibility
        chunk_doc.metadata = chunk_doc.metadata if isinstance(chunk_doc.metadata, dict) else {}
        final_docs_with_ids.append({"id": str(uuid.uuid4()), "document": chunk_doc})
        
    print(f"Processed {len(initial_documents)} initial documents, resulting in {len(final_docs_with_ids)} chunks for strategy '{strategy}'.")
    return final_docs_with_ids

def _embed_and_store_documents(docs_with_ids, embeddings_service, collection_name, env_vars, getconn_func):
    pg_vector_connection_string = f"postgresql+pg8000://{env_vars['db_user']}:{env_vars['db_pass']}@placeholder_host/{env_vars['db_name']}"
    print(f"Initializing PGVector store (collection: {collection_name})...")
    store = PGVector(
        collection_name=collection_name,
        embedding_function=embeddings_service,
        connection_string=pg_vector_connection_string,
        engine_args={"creator": getconn_func},
        pre_delete_collection=True,
    )
    documents_to_add = [item["document"] for item in docs_with_ids]
    ids_to_add = [item["id"] for item in docs_with_ids]
    print(f"Adding {len(documents_to_add)} documents to PGVector collection '{collection_name}'. This may take a few minutes...")
    store.add_documents(documents_to_add, ids=ids_to_add)
    print(f"Documents added successfully to PGVector collection '{collection_name}'.")

def main():
    env_vars = _get_env_vars()
    if not env_vars:
        return

    base_collection_name = env_vars["pgvector_base_collection_name"]
    print(f"Source JSON GCS Path: {env_vars['books_json_gcs_path']}")
    print(f"Using base collection name: {base_collection_name}")

    # These will be defined inside the try block after connector initialization
    connector = None 
    db_engine = None
    embeddings_service = None

    try:
        connector, db_engine, getconn_func = _init_connector_and_engine(env_vars)
        json_data_items = _download_and_parse_json(env_vars["books_json_gcs_path"])

        if not json_data_items:
            print("No JSON data loaded. Exiting.")
            return

        print(f"Initializing Vertex AI Embeddings (model: text-embedding-005, project: {env_vars['project_id']}, region: {env_vars['region']})...")
        embeddings_service = VertexAIEmbeddings(
            model_name="text-embedding-005", # Or other desired model like text-embedding-004, textembedding-gecko@003
            project=env_vars["project_id"],
            location=env_vars["region"],
        )
        logging.info("Vertex AI Embeddings service initialized.")

        chunking_strategies = ["character", "recursive", "token"]
        for strategy in chunking_strategies:
            collection_name_for_strategy = f"{base_collection_name}_{strategy}"
            print(f"\nProcessing for strategy: '{strategy}', target collection: '{collection_name_for_strategy}'")

            # Prepare documents using the current strategy
            docs_with_ids = _prepare_and_chunk_documents(json_data_items, strategy, MAX_DOCS_TO_PROCESS, CHUNK_SIZE, CHUNK_OVERLAP)
            if not docs_with_ids:
                print(f"No documents prepared for embedding with strategy '{strategy}'. Skipping.")
                continue

            # Initialize PGVector store for the current strategy
            # The connection_string uses a placeholder host because `getconn_func` (via engine_args -> creator)
            # handles the actual connection details securely using the Cloud SQL Python Connector.
            pg_vector_connection_string = f"postgresql+pg8000://{env_vars['db_user']}:{env_vars['db_pass']}@placeholder_for_connection_via_connector/{env_vars['db_name']}"

            print(f"Initializing PGVector store for collection: {collection_name_for_strategy}...")
            store = PGVector(
                collection_name=collection_name_for_strategy,
                embedding_function=embeddings_service,
                connection_string=pg_vector_connection_string,
                engine_args={"creator": getconn_func}, # Crucial for Cloud SQL Python Connector
                pre_delete_collection=True, # Ensures a fresh start for this collection each run
                # distance_strategy=DistanceStrategy.COSINE, # Default is COSINE, can be EUCLIDEAN
                # driving_mode="pg8000" # Explicitly set driver if needed, though often inferred
            )

            documents_to_add = [item["document"] for item in docs_with_ids]
            ids_to_add = [item["id"] for item in docs_with_ids]

            print(f"Adding {len(documents_to_add)} documents to PGVector collection '{collection_name_for_strategy}'. This may take a few minutes...")
            store.add_documents(documents_to_add, ids=ids_to_add)
            logging.info(f"Documents added successfully to PGVector collection '{collection_name_for_strategy}'.")

        logging.info("\nAll chunking strategies processed and data stored.")

    except Exception as e:
        print(f"An error occurred during the data loading process: {e}")
        traceback.print_exc()
    finally:
        if db_engine:
            print("Disposing SQLAlchemy engine created for getconn...")
            db_engine.dispose()
        if connector:
            print("Closing Cloud SQL Python Connector...")
            connector.close()
        print("Script finished.")

if __name__ == "__main__":
    main() 