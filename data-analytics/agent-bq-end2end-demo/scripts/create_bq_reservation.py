import os
import sys
from pathlib import Path
import dotenv
from google.cloud import bigquery_reservation_v1
from google.api_core.exceptions import NotFound, AlreadyExists
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

# Load environment variables
root_dir = Path(__file__).resolve().parents[1]
dotenv.load_dotenv(root_dir / ".env")

console = Console()

def run():
    reservation_id_env = os.environ.get("BQ_RESERVATION_ID")
    if not reservation_id_env:
        console.print(Panel(
            "[bold red]❌ BQ_RESERVATION_ID is missing inside .env![/bold red]\n\n"
            "Please add the following to your [bold].env[/bold] file:\n"
            "[bold yellow]BQ_RESERVATION_ID=projects/YOUR_PROJECT/locations/YOUR_LOCATION/reservations/YOUR_RESERVATION_NAME[/bold yellow]",
            title="Configuration Error"
        ))
        sys.exit(1)

    # Parse resource names
    # format: projects/{project}/locations/{location}/reservations/{name}
    parts = reservation_id_env.split("/")
    if len(parts) != 6 or parts[0] != "projects" or parts[2] != "locations" or parts[4] != "reservations":
        console.print(f"[bold red]❌ Invalid BQ_RESERVATION_ID format: {reservation_id_env}[/bold red]\n"
                      "Expected format: projects/{project}/locations/{location}/reservations/{name}")
        sys.exit(1)

    res_project_id = parts[1]
    location = parts[3]
    res_name = parts[5]
    
    runner_project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
    if not runner_project_id:
        console.print("[bold red]❌ GOOGLE_CLOUD_PROJECT environment variable not set. Please set it in your environment or .env file.[/bold red]")
        sys.exit(1)

    client = bigquery_reservation_v1.ReservationServiceClient()
    
    # 1. Check reservation container
    res_path = reservation_id_env
    console.print(f"\n[bold cyan]1. Checking BigQuery Reservation: [bold yellow]{res_name}[/bold yellow] in project [bold yellow]{res_project_id}[/bold yellow]...[/bold cyan]")
    
    try:
        res = client.get_reservation(name=res_path)
        console.print(f"✔️ Reservation [bold green]{res_name}[/bold green] exists. Edition: {res.edition}, Baseline Slots: {res.slot_capacity}.")
        reservation_exists = True
    except NotFound:
        console.print(f"⚠️ Reservation [bold yellow]{res_name}[/bold yellow] does not exist in project {res_project_id}.")
        reservation_exists = False

    # 2. Check Assignment
    assignment_exists = False
    if reservation_exists:
        console.print(f"[bold cyan]2. Checking CONTINUOUS assignment for runner project [bold yellow]{runner_project_id}[/bold yellow]...[/bold cyan]")
        parent = f"projects/{res_project_id}/locations/{location}/reservations/{res_name}"
        try:
            assignments = list(client.list_assignments(parent=parent))
            console.print(f"[dim]Debug: Found {len(assignments)} total assignments on this reservation.[/dim]")
            for assignment in assignments:
                console.print(f"[dim]Debug: Assignment found - Name: {assignment.name}, Assignee: {assignment.assignee}, Job Type: {assignment.job_type}[/dim]")
                job_type_str = str(assignment.job_type)
                is_continuous = (
                    "CONTINUOUS" in job_type_str or 
                    assignment.job_type == 6 or 
                    getattr(assignment.job_type, "name", "") == "CONTINUOUS"
                )
                assignee_ref = f"projects/{runner_project_id}"
                if is_continuous and (assignment.assignee == assignee_ref or assignment.assignee.endswith(runner_project_id)):
                    console.print(f"✔️ Active CONTINUOUS assignment found: [bold green]{assignment.name}[/bold green]")
                    assignment_exists = True
                    break
            if not assignment_exists:
                console.print(f"⚠️ No CONTINUOUS assignment found for runner project {runner_project_id}.")
        except Exception as e:
            console.print(f"[bold red]❌ Error listing assignments: {e}[/bold red]")

    # 3. Create flow if missing
    if not reservation_exists or not assignment_exists:
        console.print(Panel(
            f"Capacity reservation or continuous assignment is missing.\n"
            f"Reservation:      [bold yellow]{res_name}[/bold yellow] (in admin project: {res_project_id})\n"
            f"Runner Project:   [bold yellow]{runner_project_id}[/bold yellow] (assignee)\n"
            f"Location:         [bold yellow]{location}[/bold yellow]\n\n"
            f"[bold red]WARNING:[/bold red] BigQuery Enterprise edition capacity (minimum 50 slots) incurs costs while running.",
            title="Capacity Provisioning"
        ))

        user_choice = Prompt.ask(
            f"Do you want to proceed with creating a new reservation of type continuous named [bold cyan]{res_name}[/bold cyan] in [bold cyan]{res_project_id}[/bold cyan] project? (Type [bold red]{res_name}[/bold red] to confirm, or any other key to cancel)"
        )

        if user_choice != res_name:
            console.print("[bold red]Aborting script - please re-run if it was a typo[/bold red]")
            sys.exit(1)

        # Create Reservation
        if not reservation_exists:
            with console.status(f"Creating Reservation '{res_name}' in '{res_project_id}'..."):
                parent = f"projects/{res_project_id}/locations/{location}"
                reservation = bigquery_reservation_v1.Reservation(
                    edition="ENTERPRISE",
                    slot_capacity=50,  # Minimum 50 slots scale block
                    autoscale=bigquery_reservation_v1.Reservation.Autoscale(max_slots=100)
                )
                try:
                    client.create_reservation(parent=parent, reservation_id=res_name, reservation=reservation)
                    console.print(f"🎉 Reservation [bold green]{res_name}[/bold green] created successfully.")
                    reservation_exists = True
                except Exception as e:
                    console.print(f"[bold red]❌ Failed to create reservation: {e}[/bold red]")
                    sys.exit(1)

        # Create Assignment
        if not assignment_exists:
            with console.status(f"Creating CONTINUOUS assignment for '{runner_project_id}'..."):
                parent = f"projects/{res_project_id}/locations/{location}/reservations/{res_name}"
                assignment = bigquery_reservation_v1.Assignment(
                    assignee=f"projects/{runner_project_id}",
                    job_type="CONTINUOUS"
                )
                try:
                    client.create_assignment(parent=parent, assignment=assignment)
                    console.print("🎉 CONTINUOUS assignment created successfully.")
                except Exception as e:
                    console.print(f"[bold red]❌ Failed to create assignment: {e}[/bold red]")
                    sys.exit(1)

        console.print(Panel("[bold green]✨ Capacity Reservation & Assignment Configured Successfully! ✨[/bold green]"))
    else:
        console.print(Panel("[bold green]✔️ Slot capacity and assignment are fully active! Ready to execute continuous queries.[/bold green]"))

if __name__ == "__main__":
    run()
