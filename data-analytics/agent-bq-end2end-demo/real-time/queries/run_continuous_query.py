#!/usr/bin/env python3
"""
Python Harness to Run and Manage BigQuery Continuous Queries.

This harness handles environment initialization, remote Gemini model registration,
destination table provisioning, starting continuous query jobs, persisting job states,
checking status, and surgically canceling active running jobs.
"""

import os
import sys
import pathlib
import time
from pathlib import Path
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Import Rich components
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table

console = Console()

# Setup project root directory and load .env
queries_dir = Path(__file__).resolve().parent
possible_env_paths = [
    queries_dir.parent / ".env",
    queries_dir.parent.parent / ".env",
    Path.cwd() / ".env"
]

for env_path in possible_env_paths:
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.strip() and not line.startswith("#") and "=" in line:
                    key, val = line.strip().split("=", 1)
                    os.environ[key.strip()] = val.strip()
        break

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
if not PROJECT_ID:
    console.print("[bold red]ERROR:[/bold red] GOOGLE_CLOUD_PROJECT environment variable not set. Please check your .env file.")
    sys.exit(1)

DATASET_ID = os.environ.get("BIG_QUERY_DATASET_ID", "next_navigator")
REGION = os.environ.get("REGION", "us-central1")
CONNECTION_ID = "vertex_ai_conn"
MODEL_ID = "nlu_model"
DEST_TABLE = "sentiment_analysis_results"
JOB_ID_FILE = queries_dir / "running_job.id"

bq_client = bigquery.Client(project=PROJECT_ID)

def setup_resources():
    """Ensures destination table and Natural Language remote model are provisioned."""
    console.print("\n[bold cyan]✨ Provisioning Continuous Query Dependencies[/bold cyan]")
    
    # 1. Create Destination Table if missing
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{DEST_TABLE}"
    console.print("[dim]→ Why? Continuous queries require a partition-optimized table to stream incoming processed analytics records in real-time.[/dim]")
    try:
        bq_client.get_table(table_ref)
        console.print(f"✔️ Destination Table [green]{DEST_TABLE}[/green] already exists.")
    except NotFound:
        with console.status(f"Creating destination table {DEST_TABLE}...", spinner="dots") as status:
            schema = [
                bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("agent", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("session_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("invocation_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("span_id", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("text_content", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("sentiment", "STRING", mode="NULLABLE"),
                bigquery.SchemaField("entities", "JSON", mode="NULLABLE"),
            ]
            table = bigquery.Table(table_ref, schema=schema)
            # Enable partition on timestamp for performance/cost optimization
            table.time_partitioning = bigquery.TimePartitioning(
                type_=bigquery.TimePartitioningType.DAY,
                field="timestamp",
            )
            bq_client.create_table(table)
        console.print(f"🎉 Destination table [bold green]{DEST_TABLE}[/bold green] created successfully.")



    # 2. Register Remote Natural Language Model if missing
    model_ref = f"{PROJECT_ID}.{DATASET_ID}.{MODEL_ID}"
    console.print("[dim]→ Why? Registers the NLU remote model inside BigQuery so ML.UNDERSTAND_TEXT can classify sentiment and extract entities using Natural Language API natively.[/dim]")
    try:
        bq_client.get_model(model_ref)
        console.print(f"✔️ Remote Natural Language Model [green]{MODEL_ID}[/green] already registered.")
    except NotFound:
        with console.status(f"Registering Natural Language Model '{MODEL_ID}' using Connection {CONNECTION_ID}...", spinner="dots") as status:
            sql = f"""
            CREATE OR REPLACE MODEL `{model_ref}`
            REMOTE WITH CONNECTION `{PROJECT_ID}.{REGION}.{CONNECTION_ID}`
            OPTIONS (REMOTE_SERVICE_TYPE = 'CLOUD_AI_NATURAL_LANGUAGE_V1')
            """
            bq_client.query(sql).result()
        console.print(f"🎉 Remote NLU model [bold green]{MODEL_ID}[/bold green] registered successfully.")

def start_continuous_query():
    """Launches the continuous query job using QueryJobConfig."""
    console.print(Panel(
        Text.assemble(
            ("🚀 Submitting Real-Time Continuous Query Job\n\n", "bold green"),
            ("Continuous queries run endlessly on specialized serverless compute slots, ", "white"),
            ("monitoring the source table and processing incoming events with sub-second latency.", "white")
        ),
        border_style="green",
        title="[bold]START RUNNER[/bold]"
    ))

    # Assert presence of BQ_RESERVATION_ID
    bq_reservation_id = os.environ.get("BQ_RESERVATION_ID")
    if not bq_reservation_id:
        console.print(Panel(
            "[bold red]❌ BQ_RESERVATION_ID is missing inside .env![/bold red]\n\n"
            "To execute a Continuous Query, a capacity-based reservation is [bold yellow]100% required[/bold yellow].\n"
            "Please configure your reservation in [bold].env[/bold]:\n"
            "[bold yellow]BQ_RESERVATION_ID=projects/YOUR_PROJECT/locations/YOUR_LOCATION/reservations/YOUR_RESERVATION_NAME[/bold yellow]\n\n"
            "[dim]Note: You can verify and provision your reservation using: [bold]python3 scripts/create_bq_reservation.py[/bold][/dim]",
            title="Capacity Reservation Required"
        ))
        sys.exit(1)

    if JOB_ID_FILE.exists():
        current_id = JOB_ID_FILE.read_text().strip()
        console.print(f"[bold yellow]⚠️ WARNING:[/bold yellow] A continuous query job may already be running with ID: [bold cyan]{current_id}[/bold cyan]")
        console.print("[dim]Please check status or cancel it before starting a new one.[/dim]\n")
        return

    # Provision resources first
    setup_resources()

    # Load SQL query and interpolate parameters
    sql_template_path = queries_dir / "continuous_sentiment_query.sql"
    if not sql_template_path.exists():
        console.print(f"[bold red]ERROR:[/bold red] SQL Template not found at {sql_template_path}")
        return

    with open(sql_template_path) as f:
        sql_template = f.read()

    sql = sql_template.format(
        DEST_TABLE=f"{PROJECT_ID}.{DATASET_ID}.{DEST_TABLE}",
        SOURCE_TABLE=f"{PROJECT_ID}.{DATASET_ID}.agent_events_v2",
        MODEL_ID=f"{PROJECT_ID}.{DATASET_ID}.{MODEL_ID}"
    )

    # Configure query job to run continuously using direct API properties mapping
    job_config = bigquery.QueryJobConfig()
    job_config.reservation = bq_reservation_id
    job_config._properties["query"] = job_config._properties.get("query", {})
    job_config._properties["query"]["continuous"] = True
    
    try:
        with console.status("[bold green]Submitting Continuous Query Job to BigQuery...[/bold green]", spinner="dots") as status:
            query_job = bq_client.query(sql, job_config=job_config)
            job_id = query_job.job_id
        
        # Save Job ID locally
        JOB_ID_FILE.write_text(job_id)
        
        console.print(Panel(
            Text.assemble(
                ("🎉 SUCCESS: Continuous Query Job Submitted!\n\n", "bold green"),
                ("Job ID:         ", "bold white"), (f"{job_id}\n", "bold yellow"),
                ("Reservation:    ", "bold white"), (f"{bq_reservation_id}\n", "cyan"),
                ("Tracking File:  ", "bold white"), (f"{JOB_ID_FILE}\n\n", "cyan"),
                ("This query will run in the background endlessly processing events. Use status to track progress.", "white")
            ),
            border_style="green",
            title="[bold]SUBMISSION SUCCESS[/bold]"
        ))
    except Exception as e:
        console.print(f"[bold red]ERROR starting continuous query:[/bold red] {e}")

def check_status():
    """Checks the status of the continuous query job."""
    if not JOB_ID_FILE.exists():
        console.print("[bold yellow]No active continuous query job traced locally.[/bold yellow]")
        console.print("[dim]Tip: Start the query using: python3 run_continuous_query.py start[/dim]")
        return

    job_id = JOB_ID_FILE.read_text().strip()
    try:
        with console.status(f"Fetching BigQuery Job Status for [bold cyan]{job_id}[/bold cyan]...", spinner="dots") as status:
            job = bq_client.get_job(job_id, location=REGION)
            
        status_table = Table(title=f"📊 Job Status Report", show_header=True, header_style="bold cyan")
        status_table.add_column("Property", style="bold white")
        status_table.add_column("Current Value", style="yellow")
        
        status_table.add_row("Job ID", job.job_id)
        status_table.add_row("State (Continuous)", "[green]RUNNING / DONE[/green]" if job.state == "DONE" else f"[yellow]{job.state}[/yellow]")
        status_table.add_row("Created At", str(job.created))
        status_table.add_row("Execution Error", "[green]None[/green]" if not job.error_result else f"[red]{job.error_result}[/red]")
        
        console.print(status_table)
    except NotFound:
        console.print(f"[bold red]Job {job_id} not found on BigQuery.[/bold red] Cleaning up stale job ID tracking file.")
        JOB_ID_FILE.unlink(missing_ok=True)
    except Exception as e:
        console.print(f"[bold red]Error querying job details:[/bold red] {e}")

def cancel_query():
    """Cancels the running continuous query job."""
    if not JOB_ID_FILE.exists():
        console.print("[bold yellow]No active continuous query job traced locally to cancel.[/bold yellow]")
        return

    job_id = JOB_ID_FILE.read_text().strip()
    console.print(Panel(
        Text.assemble(
            ("🛑 Cancelling Continuous Query Job\n\n", "bold red"),
            ("This command sends a surgical cancel signal to BigQuery to release ", "white"),
            ("the serverless slots and stop the infinite stream analyzer.", "white")
        ),
        border_style="red"
    ))
    
    try:
        with console.status(f"[bold red]Sending Cancellation Request for {job_id}...[/bold red]", spinner="dots") as status:
            bq_client.cancel_job(job_id, location=REGION)
            JOB_ID_FILE.unlink(missing_ok=True)
        console.print(f"✔️ Cancellation request sent successfully. Local job ID tracking file removed.")
        console.print("[bold green]Cleanup completed successfully.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error canceling job:[/bold red] {e}")

def main():
    if len(sys.argv) < 2:
        console.print("[bold red]Usage:[/bold red] python3 run_continuous_query.py [start | status | cancel]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "start":
        start_continuous_query()
    elif cmd == "status":
        check_status()
    elif cmd == "cancel":
        cancel_query()
    else:
        console.print(f"[bold red]Unknown command:[/bold red] {cmd}")
        console.print("[bold cyan]Available Commands:[/bold cyan] start, status, cancel")

if __name__ == "__main__":
    main()
