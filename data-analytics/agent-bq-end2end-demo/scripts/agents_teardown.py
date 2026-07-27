import os
import sys
import subprocess
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.prompt import Confirm

console = Console()

PORTS = [8080, 8081, 8082]

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

def main():
    console.print(Panel(
        Text.assemble(
            ("⚠️ Local Agents Teardown Plan Preview\n\n", "bold yellow"),
            ("This utility will surgically terminate active local conversational agent microservices ", "white"),
            ("running on ports 8080, 8081, and 8082. Cloud resources are left completely UNTOUCHED.\n", "white")
        ),
        border_style="yellow",
        title="[bold]LOCAL PROCESSES TEARDOWN PLAN[/bold]"
    ))

    pids = find_agent_pids()
    proc_table = Table(title="Local Processes", show_header=True, header_style="bold magenta")
    proc_table.add_column("Resource Type", style="cyan")
    proc_table.add_column("Details", style="white")
    proc_table.add_column("Action", style="red")
    
    if pids:
        proc_table.add_row("Agent Microservices", f"PIDs: {pids} running on ports {PORTS}", "SIGKILL (Force Terminate)")
    else:
        proc_table.add_row("Agent Microservices", "No processes running on ports 8080, 8081, or 8082", "None (No active processes)")
    console.print(proc_table)

    if not pids:
        console.print("[green]No active agent processes found. Nothing to tear down! [/green]")
        return

    console.print("")
    confirm = Confirm.ask("[bold red]Are you sure you want to terminate these local processes?[/bold red]")
    if not confirm:
        console.print("[yellow]Teardown execution cancelled.[/yellow]")
        return

    console.print("\n[bold red]⚡ Terminating local agent processes...[/bold red]")
    for pid in pids:
        try:
            subprocess.run(f"kill -9 {pid}", shell=True, check=True)
            console.print(f"✔️ Successfully killed process [bold yellow]{pid}[/bold yellow].")
        except Exception as e:
            console.print(f"[bold red]WARNING:[/bold red] Could not kill process {pid}: {e}")

    console.print(Panel(
        Text("✨ Local conversational agents successfully stopped! ✨", style="bold green", justify="center"),
        border_style="green",
        padding=(1, 2)
    ))

if __name__ == "__main__":
    main()
