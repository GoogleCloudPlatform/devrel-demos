import os
import sys
import json
import time
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery
from google.api_core.exceptions import Conflict, NotFound

# Import Rich components for highly aesthetic terminal feedback
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

console = Console()

# Load environment variables from workspace root
root_dir = Path(__file__).resolve().parents[1]
load_dotenv(root_dir / ".env")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    console.print("[bold red]ERROR:[/bold red] GOOGLE_CLOUD_PROJECT environment variable not set. Please set it in your .env file.")
    sys.exit(1)

DATASET_ID = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")
REGION = os.environ.get("REGION", "us-central1")
CONNECTION_ID = "vertex_ai_conn"
MODEL_ID = "embedding_model"

# Header panel explaining what the bootstrap script does
console.print(Panel(
    Text.assemble(
        ("🚀 BigQuery Real-Time Analytics Bootstrap\n\n", "bold green"),
        ("This script automatically provisions BigQuery datasets, remote connections, ", "white"),
        ("IAM security bindings, remote embedding models, and seeds semantic search databases.\n", "white"),
        (f"Project: {PROJECT_ID}  |  Dataset: {DATASET_ID}  |  Region: {REGION}", "bold yellow")
    ),
    border_style="green",
    title="[bold]BOOTSTRAP INITIALIZATION[/bold]",
    subtitle="Secure Cloud Resource Setup"
))

bq_client = bigquery.Client(project=PROJECT_ID)
genai_client = genai.Client()

def create_dataset_if_not_exists():
    console.print("\n[bold cyan]1. Dataset Configuration[/bold cyan]")
    console.print("[dim]→ Why? BigQuery datasets act as logical namespaces and storage boundaries for tables and SQL ML models.[/dim]")
    
    dataset_ref = bq_client.dataset(DATASET_ID)
    try:
        ds = bq_client.get_dataset(dataset_ref)
        if ds.location.upper() != REGION.upper():
            console.print(f"⚠️ Dataset [yellow]{DATASET_ID}[/yellow] exists, but in location [bold red]{ds.location}[/bold red] instead of requested [bold yellow]{REGION}[/bold yellow].")
            console.print(f"[bold yellow]Deleting existing dataset to recreate in {REGION}...[/bold yellow]")
            bq_client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
            raise NotFound("Recreating in correct location")
        console.print(f"✔️ Dataset [green]{DATASET_ID}[/green] already exists in location [green]{REGION}[/green].")
    except NotFound:
        with console.status(f"[bold yellow]Creating dataset '{DATASET_ID}' in {REGION}...[/bold yellow]", spinner="dots") as status:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = REGION
            bq_client.create_dataset(dataset, timeout=30)
        console.print(f"🎉 Dataset [bold green]{DATASET_ID}[/bold green] created successfully.")

def get_connection_service_account():
    cmd = f"bq show --connection --project_id={PROJECT_ID} --location={REGION} {CONNECTION_ID}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if "serviceAccountId" in line:
                return line.split(":")[-1].strip().strip('"').strip('}').strip('"').strip()
    return None

def create_connection_if_not_exists():
    console.print("\n[bold cyan]2. BigQuery Connection Setup & IAM Security Delegation[/bold cyan]")
    console.print("[dim]→ Why? A CLOUD_RESOURCE connection acts as a secure identity bridge, letting BigQuery execute Vertex AI remote models.[/dim]")
    
    cmd = f"bq show --connection --project_id={PROJECT_ID} --location={REGION} {CONNECTION_ID}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        console.print(f"✔️ BigQuery Connection [green]{CONNECTION_ID}[/green] already exists.")
    else:
        with console.status(f"[bold yellow]Creating Connection '{CONNECTION_ID}'...[/bold yellow]", spinner="dots") as status:
            create_cmd = f"bq mk --connection --location={REGION} --project_id={PROJECT_ID} --connection_type=CLOUD_RESOURCE {CONNECTION_ID}"
            subprocess.run(create_cmd, shell=True, check=True)
        console.print(f"🎉 Connection [bold green]{CONNECTION_ID}[/bold green] created successfully.")

    sa = get_connection_service_account()
    if sa:
        console.print(f"✔️ Retracted Connection Service Account: [bold yellow]{sa}[/bold yellow]")
        console.print("[dim]→ Why? This service account must be granted permissions to call Vertex AI models so BigQuery ML queries can authenticate safely.[/dim]")
        
        roles = ["roles/aiplatform.user", "roles/cloudaicompanion.user", "roles/serviceusage.serviceUsageConsumer"]
        max_iam_retries = 20
        for role in roles:
            for attempt in range(max_iam_retries):
                try:
                    with console.status(f"[bold yellow]Delegating {role} to Connection Service Account (Attempt {attempt+1}/{max_iam_retries})...[/bold yellow]", spinner="dots") as status:
                        grant_cmd = f"gcloud projects add-iam-policy-binding {PROJECT_ID} --member=serviceAccount:{sa} --role={role} --no-user-output-enabled"
                        subprocess.run(grant_cmd, shell=True, check=True)
                    console.print(f"✔️ Granted [green]{role}[/green] successfully.")
                    break
                except subprocess.CalledProcessError as e:
                    if attempt < max_iam_retries - 1:
                        console.print(f"[bold yellow]⚠️ Service account not yet available or IAM propagation latency (Attempt {attempt+1}/{max_iam_retries}). Retrying in 10s...[/bold yellow]")
                        time.sleep(10)
                    else:
                        raise e
    else:
        console.print("[bold red]WARNING:[/bold red] Service Account for connection not found. Could not grant IAM roles.")

def create_remote_model():
    from google.api_core.exceptions import BadRequest
    console.print("\n[bold cyan]3. BigQuery ML Remote Embedding Model[/bold cyan]")
    console.print("[dim]→ Why? Registers the text-embedding-005 model in BigQuery so you can compute semantic embeddings directly in standard SQL.[/dim]")
    
    sql = f"""
    CREATE OR REPLACE MODEL `{PROJECT_ID}.{DATASET_ID}.{MODEL_ID}`
    REMOTE WITH CONNECTION `{PROJECT_ID}.{REGION}.{CONNECTION_ID}`
    OPTIONS (ENDPOINT = 'text-embedding-005')
    """
    
    max_retries = 20
    for attempt in range(max_retries):
        try:
            with console.status(f"[bold yellow]Registering model {MODEL_ID} inside BigQuery (Attempt {attempt+1}/{max_retries})...[/bold yellow]", spinner="dots") as status:
                query_job = bq_client.query(sql)
                query_job.result()
            console.print(f"🎉 Remote model [bold green]{MODEL_ID}[/bold green] registered successfully inside BigQuery.")
            return
        except BadRequest as e:
            err_msg = str(e).lower()
            if "permission" in err_msg or "role" in err_msg or "access" in err_msg:
                console.print(f"[bold yellow]⚠️ IAM permission/access not yet propagated (Attempt {attempt+1}/{max_retries}). Retrying in 10s...[/bold yellow]")
                time.sleep(10)
            else:
                raise e
    raise RuntimeError("Failed to register Remote Embedding Model due to IAM propagation timeout.")

def create_nlu_model():
    from google.api_core.exceptions import BadRequest
    console.print("\n[bold cyan]3.5 Cloud AI Natural Language NLU Model[/bold cyan]")
    console.print("[dim]→ Why? Registers the NLU remote model inside BigQuery so ML.UNDERSTAND_TEXT can classify sentiment and extract entities using Natural Language API natively.[/dim]")
    
    nlu_model_id = "nlu_model"
    model_ref = f"{PROJECT_ID}.{DATASET_ID}.{nlu_model_id}"
    
    sql = f"""
    CREATE OR REPLACE MODEL `{model_ref}`
    REMOTE WITH CONNECTION `{PROJECT_ID}.{REGION}.{CONNECTION_ID}`
    OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_NATURAL_LANGUAGE_V1')
    """
    
    max_retries = 20
    for attempt in range(max_retries):
        try:
            with console.status(f"[bold yellow]Registering NLU Model {nlu_model_id} (Attempt {attempt+1}/{max_retries})...[/bold yellow]", spinner="dots") as status:
                query_job = bq_client.query(sql)
                query_job.result()
            console.print(f"🎉 Remote NLU model [bold green]{nlu_model_id}[/bold green] registered successfully inside BigQuery.")
            return
        except BadRequest as e:
            err_msg = str(e).lower()
            if "permission" in err_msg or "role" in err_msg or "access" in err_msg:
                console.print(f"[bold yellow]⚠️ IAM permission/access not yet propagated (Attempt {attempt+1}/{max_retries}). Retrying in 10s...[/bold yellow]")
                time.sleep(10)
            else:
                raise e
    raise RuntimeError("Failed to register Remote NLU Model due to IAM propagation timeout.")

def seed_tables():
    console.print("\n[bold cyan]4. Knowledge Database Schema Setup & Semantic Vector Seeding[/bold cyan]")
    console.print("[dim]→ Why? We generate high-dimensional embeddings using Gemini and save them into BigQuery to power real-time Semantic Vector Search.[/dim]")
    
    hotel_table_id = f"{PROJECT_ID}.{DATASET_ID}.venue_knowledge"
    stadium_table_id = f"{PROJECT_ID}.{DATASET_ID}.stadium_logistics"

    hotel_schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("poi_type", "STRING"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("location_summary", "STRING"),
        bigquery.SchemaField("description", "STRING"),
        bigquery.SchemaField("vector_content", "STRING"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    ]

    stadium_schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("policy_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("details", "STRING"),
        bigquery.SchemaField("category", "STRING"),
        bigquery.SchemaField("vector_content", "STRING"),
        bigquery.SchemaField("embedding", "FLOAT64", mode="REPEATED"),
    ]

    # Create Tables
    for name, table_id, schema in [("Venue Knowledge", hotel_table_id, hotel_schema), ("Stadium Logistics", stadium_table_id, stadium_schema)]:
        try:
            bq_client.get_table(table_id)
            console.print(f"✔️ Table [green]{name}[/green] already exists.")
        except NotFound:
            with console.status(f"[bold yellow]Creating Table '{name}'...[/bold yellow]", spinner="dots") as status:
                table = bigquery.Table(table_id, schema=schema)
                bq_client.create_table(table)
            console.print(f"🎉 Table [bold green]{name}[/bold green] created successfully.")

    # Load source payload
    payload_path = root_dir / "data" / "enriched_payload.json"
    if not payload_path.exists():
        console.print(f"[bold red]ERROR:[/bold red] Source payload not found at {payload_path}")
        return

    with open(payload_path) as f:
        data = json.load(f)

    # Helper to generate embeddings via GenAI SDK
    def get_embedding(text):
        res = genai_client.models.embed_content(
            model="text-embedding-005",
            contents=text
        )
        return res.embeddings[0].values

    # Seed Hotel POIs
    hotel_rows = []
    with console.status("[bold yellow]Computing Gemini vector embeddings and seeding Hotel POIs...[/bold yellow]", spinner="dots") as status:
        for item in data.get("hotel", []):
            vector_text = f"POI: {item['name']}. Type: {item['poi_type']}. Location: {item['location_summary']}. Description: {item['description']}"
            embedding = get_embedding(vector_text)
            hotel_rows.append({
                "id": item["id"],
                "name": item["name"],
                "poi_type": item["poi_type"],
                "category": item["category"],
                "location_summary": item["location_summary"],
                "description": item["description"],
                "vector_content": vector_text,
                "embedding": embedding
            })
        if hotel_rows:
            bq_client.insert_rows_json(hotel_table_id, hotel_rows)
    console.print(f"🎉 Seeded [bold green]{len(hotel_rows)}[/bold green] Hotel POI rows with high-fidelity vector embeddings.")

    # Seed Stadium Policies
    stadium_rows = []
    with console.status("[bold yellow]Computing Gemini vector embeddings and seeding Stadium Policies...[/bold yellow]", spinner="dots") as status:
        for item in data.get("stadium", []):
            vector_text = f"Policy: {item['policy_name']}. Details: {item['details']}. Category: {item['category']}"
            embedding = get_embedding(vector_text)
            stadium_rows.append({
                "id": item["id"],
                "policy_name": item["policy_name"],
                "details": item["details"],
                "category": item["category"],
                "vector_content": vector_text,
                "embedding": embedding
            })
        if stadium_rows:
            bq_client.insert_rows_json(stadium_table_id, stadium_rows)
    console.print(f"🎉 Seeded [bold green]{len(stadium_rows)}[/bold green] Stadium Policy rows with high-fidelity vector embeddings.")

if __name__ == "__main__":
    try:
        create_dataset_if_not_exists()
        create_connection_if_not_exists()
        create_remote_model()
        create_nlu_model()
        seed_tables()
        console.print(Panel(
            Text("✨ Cloud Bootstrap Completed Successfully! ✨", style="bold green", justify="center"),
            border_style="green",
            padding=(1, 2)
        ))
    except Exception as e:
        console.print(f"\n[bold red]❌ BOOTSTRAP FAILED:[/bold red] {e}")
        sys.exit(1)
