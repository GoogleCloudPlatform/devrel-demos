import os
import pg8000
from google.cloud.sql.connector import Connector
import sqlalchemy
import logging
import google.cloud.logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

load_dotenv() 

def main():
    # db_instance_connection_name = os.getenv("DB_INSTANCE_CONNECTION_NAME")
    project_id = os.getenv("PROJECT_ID")
    sql_instance_name = os.getenv("SQL_INSTANCE_NAME")
    region = os.getenv("REGION")
    db_name = os.getenv("SQL_DATABASE_NAME")
    db_user = os.getenv("SQL_USER")
    db_pass = os.getenv("SQL_PASSWORD")
    db_instance_connection_name = f"{project_id}:{region}:{sql_instance_name}"


    if not all([db_instance_connection_name, db_name, db_user, db_pass]):
        print("Error: SQL connection environment variables not set.")
        print("Ensure DB_INSTANCE_CONNECTION_NAME, SQL_DATABASE_NAME, SQL_USER, SQL_PASSWORD are set.")
        return

    print(f"Connecting to Cloud SQL instance: {db_instance_connection_name}, database: {db_name}")

    connector = Connector()

    def getconn() -> pg8000.dbapi.Connection:
        conn: pg8000.dbapi.Connection = connector.connect(
            db_instance_connection_name, # Cloud SQL instance connection name
            "pg8000",
            user=db_user,
            password=db_pass,
            db=db_name,
            ip_type="public" # Use "public" for Public IP, "private" for Private IP
        )
        return conn

    try:
        pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
        with pool.connect() as db_conn:
            # Check if the extension is already enabled
            result = db_conn.execute(sqlalchemy.text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).fetchone()
            if result:
                logging.info("pgvector extension is already enabled.")
            else:
                # If not enabled, try to create it
                logging.info("Enabling pgvector extension...")
                db_conn.execute(sqlalchemy.text("CREATE EXTENSION IF NOT EXISTS vector;"))
                db_conn.commit()  # Commit the transaction to make the extension permanent
                logging.info("pgvector extension enabled successfully.")

            # Verify by selecting from pg_extension again
            result_after_creation = db_conn.execute(sqlalchemy.text("SELECT extname FROM pg_extension WHERE extname = 'vector';")).fetchone()
            if result_after_creation:
                logging.info(f"Successfully verified '{result_after_creation[0]}' extension is active.")
            else:
                logging.info("Error: pgvector extension could not be verified after attempting to create it.")

        print("Cloud SQL database is ready for vector operations (or was already).")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Detailed traceback:")
        import traceback
        traceback.print_exc()
    finally:
        if 'pool' in locals() and pool:
            pool.dispose()
        if connector: # check if connector was initialized
            connector.close()

if __name__ == "__main__":
    main() 