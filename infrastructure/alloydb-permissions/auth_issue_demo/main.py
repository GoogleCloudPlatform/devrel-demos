import os
import logging
from flask import Flask
from google.cloud.alloydb.connector import Connector
import sqlalchemy

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from Environment Variables
# The fully qualified instance URI: projects/<PROJECT>/locations/<REGION>/clusters/<CLUSTER>/instances/<INSTANCE>
ALLOYDB_URI = os.environ.get("ALLOYDB_URI") 
DB_USER = os.environ.get("DB_USER", "auth-debug")
DB_PASS = os.environ.get("DB_PASS", "debug-auth")
DB_NAME = os.environ.get("DB_NAME", "postgres")
USE_PUBLIC_IP = os.environ.get("USE_PUBLIC_IP", "false").lower() == "true"

# Initialize Connector lazily
_connector = None

def get_connector():
    global _connector
    if _connector is None:
        _connector = Connector()
    return _connector

def getconn():
    connector = get_connector()
    ip_type = "PUBLIC" if USE_PUBLIC_IP else "PRIVATE"
    
    conn = connector.connect(
        ALLOYDB_URI,
        "pg8000",
        user=DB_USER,
        password=DB_PASS,
        db=DB_NAME,
        ip_type=ip_type
    )
    return conn

@app.route("/")
def index():
    return "AlloyDB Auth Demo. /connect to test.", 200

@app.route("/connect")
def connect_db():
    if not ALLOYDB_URI:
        return "FAILURE: ALLOYDB_URI env var is not set.", 500

    try:
        logger.info(f"Attempting connection to {ALLOYDB_URI} with user {DB_USER}...")
        
        # Create connection pool
        pool = sqlalchemy.create_engine(
            "postgresql+pg8000://",
            creator=getconn,
        )
        
        with pool.connect() as db_conn:
            # Simple query to validate connection
            result = db_conn.execute(sqlalchemy.text("SELECT NOW()")).fetchone()
            timestamp = result[0]
            
        msg = f"SUCCESS: Connected to AlloyDB! DB Time: {timestamp}"
        logger.info(msg)
        return msg, 200

    except Exception as e:
        logger.exception("Connection failed")
        # Return the error to the caller to visualize the auth failure
        return f"FAILURE: Connection Error.\nDetails: {str(e)}", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
