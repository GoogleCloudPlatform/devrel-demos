import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery
from google.api_core.exceptions import NotFound

# Import Rich elements
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from google.cloud import bigquery_reservation_v1
from rich.prompt import Confirm, Prompt

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
BQ_RESERVATION_ID = os.environ.get("BQ_RESERVATION_ID")

PORTS = [8080, 8081, 8082]
bq_client = bigquery.Client(project=PROJECT_ID)

def find_agent_pids():
    """Finds PIDs of processes running on ports 8080, 8081, 8082."""
    pids = set()
    for port in PORTS:
        cmd = f"lsof -t -i:{port}"
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.strip().split("\n"):
                if line.strip():
                    pids.add(int(line.strip()))
    return sorted(list(pids))

def get_connection_service_account():
    """Retrieves the service account associated with the connection, if it exists."""
    cmd = f"bq show --connection --project_id={PROJECT_ID} --location={REGION} {CONNECTION_ID}"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        for line in result.stdout.split("\n"):
            if "serviceAccountId" in line:
                return line.split(":")[-1].strip().strip('"').strip('}').strip('"').strip()
    return None

def main():
    console.print(Panel(
        Text.assemble(
            ("⚠️ Surgical Teardown Plan Preview\n\n", "bold red"),
            ("This utility will surgically delete all provisioned GCP cloud resources ", "white"),
            ("and terminate any active background local agent processes.\n", "white"),
            (f"Target Project: {PROJECT_ID}  |  Dataset to Drop: {DATASET_ID}", "bold yellow")
        ),
        border_style="red",
        title="[bold]TEARDOWN ALL PLAN[/bold]"
    ))

    # 1. Local Processes Table
    pids = find_agent_pids()
    proc_table = Table(title="1. Local Processes", show_header=True, header_style="bold magenta")
    proc_table.add_column("Resource Type", style="cyan")
    proc_table.add_column("Details", style="white")
    proc_table.add_column("Action", style="red")
    
    if pids:
        proc_table.add_row("Agent Microservices", f"PIDs: {pids} running on ports {PORTS}", "SIGKILL (Force Terminate)")
    else:
        proc_table.add_row("Agent Microservices", "No processes running on ports 8080, 8081, or 8082", "None (No active processes)")
    console.print(proc_table)

    # 1.5. Continuous Query Check
    job_id_file = root_dir / "real-time" / "queries" / "running_job.id"
    cq_job_id = job_id_file.read_text().strip() if job_id_file.exists() else None

    # 2. BigQuery Assets Table
    bq_table = Table(title="2. BigQuery Assets & Schema", show_header=True, header_style="bold blue")
    bq_table.add_column("Asset Name", style="cyan")
    bq_table.add_column("Resource ID / Reference", style="yellow")
    bq_table.add_column("Action", style="red")
    
    tables_to_delete = ["venue_knowledge", "stadium_logistics", "sentiment_analysis_results", "agent_events_v2"]
    models_to_delete = [MODEL_ID, "sentiment_gemini_model", "nlu_model"]
    
    if cq_job_id:
        bq_table.add_row("Continuous Query Job", f"Job ID: {cq_job_id}", "CANCEL / ABORT")
    for tbl in tables_to_delete:
        bq_table.add_row("Table / Stream", f"{DATASET_ID}.{tbl}", "DELETE")
    for mdl in models_to_delete:
        bq_table.add_row("SQL Remote Model", f"{DATASET_ID}.{mdl}", "DROP MODEL")
    bq_table.add_row("BigQuery Dataset", f"{DATASET_ID}", "DROP DATASET (CASCADE)")
    console.print(bq_table)

    # 3. Connection and IAM bindings Table
    conn_table = Table(title="3. Cloud Resource Connections & IAM Delegation", show_header=True, header_style="bold green")
    conn_table.add_column("Resource Name", style="cyan")
    conn_table.add_column("Identity / Principle", style="yellow")
    conn_table.add_column("Action", style="red")
    
    sa = get_connection_service_account()
    if sa:
        conn_table.add_row("BigQuery Connection", f"connection_id: '{CONNECTION_ID}'", "DELETE")
        conn_table.add_row(
            "IAM Policy Binding", 
            f"Service Account: {sa}\nRoles: roles/aiplatform.user\n       roles/cloudaicompanion.user\n       roles/serviceusage.serviceUsageConsumer", 
            "REMOVE BINDING"
        )
    else:
        conn_table.add_row("Connection & IAM", f"Connection '{CONNECTION_ID}' not found", "None (Already deleted)")
    console.print(conn_table)

    delete_reservation = False
    if BQ_RESERVATION_ID:
        console.print("")
        if Confirm.ask("[bold yellow]Do you want to delete the BigQuery reservation associated with this project as well?[/bold yellow]"):
            user_input = Prompt.ask(
                f"[bold red]Please confirm by typing the entire reservation resource path exactly[/bold red]\n"
                f"[dim]({BQ_RESERVATION_ID})[/dim]"
            )
            if user_input.strip() == BQ_RESERVATION_ID.strip():
                delete_reservation = True
                console.print("[bold green]✔️ Reservation deletion confirmed and added to the teardown plan.[/bold green]")
            else:
                console.print("[bold red]❌ Confirmation mismatch. Reservation will NOT be deleted.[/bold red]")

    console.print("")
    confirm = Confirm.ask("[bold red]Are you sure you want to execute this complete teardown?[/bold red]")
    if not confirm:
        console.print("[yellow]Teardown execution cancelled.[/yellow]")
        return

    console.print("\n[bold red]⚡ Executing Complete Surgical Teardown...[/bold red]")

    # 0. Cancel Active Continuous Query
    if cq_job_id:
        with console.status(f"[bold red]Cancelling active Continuous Query Job: {cq_job_id}...[/bold red]", spinner="dots") as status:
            try:
                bq_client.cancel_job(cq_job_id, location=REGION)
                console.print(f"✔️ Cancel request submitted for Continuous Query Job [bold yellow]{cq_job_id}[/bold yellow].")
            except Exception as e:
                console.print(f"[bold yellow]⚠️ Note: Could not cancel continuous query job: {e}[/bold yellow]")
        job_id_file.unlink(missing_ok=True)

    # 1. Kill Processes
    if pids:
        with console.status("[bold red]Terminating local agent processes...[/bold red]", spinner="dots") as status:
            for pid in pids:
                try:
                    subprocess.run(f"kill -9 {pid}", shell=True, check=True)
                    console.print(f"✔️ Successfully killed process [bold yellow]{pid}[/bold yellow].")
                except Exception as e:
                    console.print(f"[bold red]WARNING:[/bold red] Could not kill process {pid}: {e}")

    # 2. Delete Tables & Models
    for tbl in tables_to_delete:
        table_ref = f"{PROJECT_ID}.{DATASET_ID}.{tbl}"
        with console.status(f"[bold red]Deleting table {tbl}...[/bold red]", spinner="dots") as status:
            bq_client.delete_table(table_ref, not_found_ok=True)
        console.print(f"✔️ Deleted table: [bold yellow]{table_ref}[/bold yellow]")

    for mdl in models_to_delete:
        model_ref = f"{PROJECT_ID}.{DATASET_ID}.{mdl}"
        with console.status(f"[bold red]Dropping remote model {mdl}...[/bold red]", spinner="dots") as status:
            sql = f"DROP MODEL IF EXISTS `{model_ref}`"
            bq_client.query(sql).result()
        console.print(f"✔️ Dropped remote model: [bold yellow]{model_ref}[/bold yellow]")

    # 3. Delete IAM bindings before connection is removed
    if sa:
        console.print("[bold red]Removing delegated project IAM policy bindings...[/bold red]")
        for role in ["roles/aiplatform.user", "roles/cloudaicompanion.user", "roles/serviceusage.serviceUsageConsumer"]:
            with console.status(f"Removing {role} assignment...", spinner="dots") as status:
                iam_cmd = (
                    f"gcloud projects remove-iam-policy-binding {PROJECT_ID} "
                    f"--member='serviceAccount:{sa}' --role='{role}' "
                    f"--project={PROJECT_ID} --billing-project={PROJECT_ID} --no-user-output-enabled"
                )
                res = subprocess.run(iam_cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                console.print(f"✔️ Successfully removed [bold yellow]{role}[/bold yellow] from service account.")
            else:
                console.print(f"[bold red]ERROR:[/bold red] Failed to remove {role}: {res.stderr.strip()}")

    # 4. Delete Connection
    with console.status("[bold red]Deleting BigQuery Connection...[/bold red]", spinner="dots") as status:
        del_conn_cmd = f"bq rm --connection --location={REGION} --project_id={PROJECT_ID} -f {CONNECTION_ID}"
        res = subprocess.run(del_conn_cmd, shell=True, capture_output=True, text=True)
    if res.returncode == 0:
        console.print(f"✔️ Successfully deleted BigQuery Connection: [bold yellow]{CONNECTION_ID}[/bold yellow]")
    else:
        if "Not found" in res.stderr:
            console.print(f"✔️ Connection [bold yellow]{CONNECTION_ID}[/bold yellow] was already deleted.")
        else:
            console.print(f"[bold red]ERROR:[/bold red] Failed to delete connection: {res.stderr.strip()}")

    # 5. Delete Dataset
    with console.status("[bold red]Deleting BigQuery Dataset...[/bold red]", spinner="dots") as status:
        dataset_ref = bq_client.dataset(DATASET_ID)
        bq_client.delete_dataset(dataset_ref, delete_contents=True, not_found_ok=True)
    console.print(f"✔️ Successfully deleted Dataset: [bold yellow]{DATASET_ID}[/bold yellow]")

    # 5.5. Delete Reservation if requested
    if delete_reservation and BQ_RESERVATION_ID:
        with console.status(f"[bold red]Deleting BigQuery Reservation {BQ_RESERVATION_ID}...[/bold red]", spinner="dots") as status:
            try:
                res_client = bigquery_reservation_v1.ReservationServiceClient()
                res_client.delete_reservation(name=BQ_RESERVATION_ID)
                console.print(f"✔️ Successfully deleted Reservation: [bold yellow]{BQ_RESERVATION_ID}[/bold yellow]")
            except Exception as e:
                console.print(f"[bold red]ERROR deleting reservation:[/bold red] {e}")

    console.print(Panel(
        Text("✨ All local processes terminated and GCP assets successfully dropped! ✨", style="bold green", justify="center"),
        border_style="green",
        padding=(1, 2)
    ))

if __name__ == "__main__":
    main()
