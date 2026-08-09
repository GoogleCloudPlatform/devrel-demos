#!/usr/bin/env python3
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.cloud import bigquery

# Import Rich components for a highly premium CLI output
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# Resolve workspace root and load environment variables
root_dir = Path(__file__).resolve().parents[1]
load_dotenv(root_dir / ".env")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    console.print("[bold red]❌ ERROR: GOOGLE_CLOUD_PROJECT environment variable not set. Please check your .env file.[/bold red]")
    sys.exit(1)

DATASET_ID = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")
stadium_table_id = f"{PROJECT_ID}.{DATASET_ID}.stadium_logistics"

# Initialize Google GenAI and BigQuery Clients
try:
    genai_client = genai.Client()
    bq_client = bigquery.Client(project=PROJECT_ID)
except Exception as e:
    console.print(f"[bold red]❌ Failed to initialize GCP clients: {e}[/bold red]")
    sys.exit(1)

def get_embedding(text):
    """Computes high-dimensional vector embeddings using the exact same text-embedding-005 model."""
    try:
        res = genai_client.models.embed_content(
            model="text-embedding-005",
            contents=text
        )
        return res.embeddings[0].values
    except Exception as e:
        console.print(f"[bold red]❌ Failed to generate embedding with text-embedding-005: {e}[/bold red]")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Update and re-embed RAG bag policies in BigQuery.")
    parser.add_argument("action", choices=["allow", "revert"], help="Action: 'allow' (Gate 4 free check) or 'revert' (No lockers)")
    args = parser.parse_args()

    # Dynamically locate the rag-augment directory relative to the workspace root
    rag_augment_dir = root_dir / "rag-augment"
    if args.action == "allow":
        sql_file = rag_augment_dir / "bag_policy_allow_update.sql"
        title = "Updating Bag Policy to ALLOW Free Bag Check"
        color = "green"
    else:
        sql_file = rag_augment_dir / "bag_policy_none.sql"
        title = "Reverting Bag Policy to NO LOCKERS Restriction"
        color = "yellow"

    if not sql_file.exists():
        console.print(f"[bold red]❌ SQL Template not found at: {sql_file}[/bold red]")
        sys.exit(1)

    # 1. Read and format the SQL template
    sql_template = sql_file.read_text()
    sql_query = sql_template.replace("{PROJECT_ID}", PROJECT_ID).replace("{DATASET_ID}", DATASET_ID)

    console.print(Panel(
        Text.assemble(
            (f"⚡ {title}\n\n", f"bold {color}"),
            (f"Project: {PROJECT_ID}  |  Dataset: {DATASET_ID}\n", "dim"),
            (f"SQL Template: {sql_file.name}", "dim yellow")
        ),
        border_style=color
    ))

    # 2. Run the text update DML in BigQuery
    try:
        with console.status(f"[bold {color}]Executing DML update in BigQuery...[/bold {color}]", spinner="dots"):
            query_job = bq_client.query(sql_query)
            query_job.result()
        console.print(f"✔️ BigQuery DML Update completed successfully.")
    except Exception as e:
        console.print(f"[bold red]❌ BigQuery query failed: {e}[/bold red]")
        sys.exit(1)

    # 3. Fetch the updated row to compute its embedding
    try:
        fetch_sql = f"SELECT details, vector_content FROM `{stadium_table_id}` WHERE id = 's_004'"
        row = list(bq_client.query(fetch_sql).result())[0]
        details = row.details
        vector_content = row.vector_content
    except Exception as e:
        console.print(f"[bold red]❌ Failed to retrieve updated details from table: {e}[/bold red]")
        sys.exit(1)

    # 4. Generate new vector embedding
    console.print(f"📝 Computing vector embedding using [bold cyan]text-embedding-005[/bold cyan] for content:")
    console.print(f"[dim italic]\"{vector_content}\"[/dim italic]")
    
    with console.status("[bold cyan]Generating vector embedding via Gemini API...[/bold cyan]", spinner="dots"):
        embedding = get_embedding(vector_content)

    # 5. Push the computed vector back into BigQuery
    update_vector_sql = f"""
    UPDATE `{stadium_table_id}`
    SET embedding = @embedding
    WHERE id = 's_004'
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("embedding", "FLOAT64", embedding)
        ]
    )

    try:
        with console.status(f"[bold {color}]Updating vector embedding inside table...[/bold {color}]", spinner="dots"):
            query_job = bq_client.query(update_vector_sql, job_config=job_config)
            query_job.result()
        console.print(Panel(f"🎉 SUCCESS: Policy s_004 updated and vector re-embedded with text-embedding-005!", subtitle="Ready for testing in Playground", subtitle_align="right", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]❌ Failed to update embedding column: {e}[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
