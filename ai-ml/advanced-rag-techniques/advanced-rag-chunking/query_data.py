import os
import pg8000 # type: ignore
from google.cloud.sql.connector import Connector, IPTypes
from langchain_community.vectorstores.pgvector import PGVector, DistanceStrategy
from langchain_google_vertexai import VertexAIEmbeddings
import traceback
import traceback
import logging
import google.cloud.logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv() 

# Global constant for query output (can be modified by user as per interactive steps)
MAX_OUTPUT_CONTENT_LENGTH = 200 

def main():
    # Retrieve environment variables
    project_id = os.getenv("PROJECT_ID")
    region = os.getenv("REGION")
    sql_instance_name = os.getenv("SQL_INSTANCE_NAME")
    db_name = os.getenv("SQL_DATABASE_NAME")
    db_user = os.getenv("SQL_USER")
    db_pass = os.getenv("SQL_PASSWORD")
    base_collection_name = os.getenv("PGVECTOR_BASE_COLLECTION_NAME")
    db_instance_connection_name = f"{project_id}:{region}:{sql_instance_name}"


    required_vars = {
        "PROJECT_ID": project_id,
        "REGION": region,
        "DB_INSTANCE_CONNECTION_NAME": db_instance_connection_name,
        "SQL_DATABASE_NAME": db_name,
        "SQL_USER": db_user,
        "SQL_PASSWORD": db_pass,
        "PGVECTOR_BASE_COLLECTION_NAME": base_collection_name
    }

    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        print(f"Error: Required environment variables are not fully set: {', '.join(missing_vars)}")
        print("Please ensure all required environment variables are set (PROJECT_ID, REGION, DB_INSTANCE_CONNECTION_NAME, SQL_DATABASE_NAME, SQL_USER, SQL_PASSWORD, PGVECTOR_BASE_COLLECTION_NAME).")
        return

    print(f"Starting query process for database: '{db_name}', using base collection: '{base_collection_name}'")

    connector = None
    embeddings_service = None

    try:
        print("Initializing Cloud SQL Python Connector for querying...")
        connector = Connector()

        def getconn() -> pg8000.dbapi.Connection:
            conn = connector.connect(
                db_instance_connection_name, "pg8000", user=db_user, password=db_pass,
                db=db_name, ip_type=IPTypes.PUBLIC, enable_iam_auth=False
            )
            return conn

        print(f"Initializing Vertex AI Embeddings (model: text-embedding-005, project: {project_id}, location: {region}) for querying...")
        embeddings_service = VertexAIEmbeddings(
            model_name="text-embedding-005",
            project=project_id,
            location=region
        )
        logging.info("Vertex AI Embeddings service initialized for querying.")
        
        query = "Tell me about the Dursleys and their relationship with Harry Potter" # You can change this query later
        print(f"\nUsing query: \"{query}\"\n")

        chunking_strategies = ["character", "recursive", "token"]
        pg_vector_connection_string = f"postgresql+pg8000://{db_user}:{db_pass}@placeholder_for_connection_via_connector/{db_name}"

        for strategy in chunking_strategies:
            collection_name_for_strategy = f"{base_collection_name}_{strategy}"
            print(f"--- Preparing to query for {strategy.upper()} Chunking Strategy (Collection: {collection_name_for_strategy}) ---")

            try:
                logging.info(f"  Initializing PGVector store for {collection_name_for_strategy}...")
                store = PGVector(
                    collection_name=collection_name_for_strategy,
                    embedding_function=embeddings_service, # Crucial for query embedding
                    connection_string=pg_vector_connection_string,
                    engine_args={"creator": getconn}, # For Cloud SQL Python Connector
                    # distance_strategy=DistanceStrategy.COSINE # Ensure this matches loading if specified
                )

                logging.info(f"  Performing similarity search for collection {collection_name_for_strategy}...")
                # Retrieve top 3 documents with their scores
                retrieved_docs_with_scores = store.similarity_search_with_score(query, k=3)

                if not retrieved_docs_with_scores:
                    print("    No documents found. Possible reasons: Collection is empty, query is too dissimilar, or an issue with connection/setup.")
                else:
                    logging.info(f"    Found {len(retrieved_docs_with_scores)} relevant documents:")
                    for i, (doc, score) in enumerate(retrieved_docs_with_scores):
                        content_preview = doc.page_content[:MAX_OUTPUT_CONTENT_LENGTH] # Truncate for display
                        if len(doc.page_content) > MAX_OUTPUT_CONTENT_LENGTH:
                            content_preview += "..."
                        print(f"      Result {i+1} (Relevance Score: {score:.4f}):")
                        print(f"        Content: \"{content_preview}\"")
                        if doc.metadata:
                            # Display source if available, or any other relevant metadata
                            source = doc.metadata.get('source', 'N/A')
                            print(f"        Metadata: source='{source}', other_metadata_keys={list(doc.metadata.keys())}")
                        print("        " + "-" * 30)
            except Exception as e_store:
                print(f"    Error querying collection '{collection_name_for_strategy}': {e_store}")
                traceback.print_exc() # Print full traceback for store-specific errors
            print("\n")

    except Exception as e:
        print(f"An overall error occurred during the querying process: {e}")
        traceback.print_exc()
    finally:
        if connector:
            print("Closing Cloud SQL Python Connector (query script)...")
            connector.close()

            # Add the flush here
            cloud_logging_client.flush_handlers()
        print("Query script finished.")

if __name__ == "__main__":
    main() 