#!/usr/bin/env python3
"""
Git Worktree Isolation Manager for Bridge Deck.
Provides non-clobbering, concurrent workspace sandboxes for autonomous agents.
Each agent operates inside a dedicated Git worktree on an independent branch.
"""

import os
import subprocess
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional

_worktree_lock = threading.Lock()


def ensure_git_repo(workspace_dir: Path) -> bool:
    """
    Ensures workspace_dir is an initialized Git repository with at least one initial commit.
    """
    workspace_dir = Path(workspace_dir).resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)
    git_dir = workspace_dir / ".git"

    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "-b", "main"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            check=True
        )
        # Configure local repo commit identity so commits never fail
        subprocess.run(
            ["git", "config", "user.name", "Bridge Deck Flow Agent"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "flow-agent@bridge-deck.internal"],
            cwd=str(workspace_dir),
            capture_output=True,
            text=True,
            check=True
        )

    # Ensure worktrees/ is in .gitignore
    gitignore = workspace_dir / ".gitignore"
    gi_content = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if "worktrees/" not in gi_content:
        with open(gitignore, "a", encoding="utf-8") as gf:
            gf.write("\n# Bridge Deck Agent Worktrees\nworktrees/\n")

    # Ensure initial commit exists (git worktree requires a commit to branch from)
    check_head = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=str(workspace_dir),
        capture_output=True,
        text=True
    )
    if check_head.returncode != 0:
        readme = workspace_dir / "README.md"
        if not readme.exists():
            readme.write_text("# Flow Simulation Project\n\nSelf-contained simulation application.\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=str(workspace_dir), capture_output=True, text=True, check=True)
        subprocess.run(["git", "commit", "-m", "Initial commit for Flow project"], cwd=str(workspace_dir), capture_output=True, text=True, check=True)

    return True


def get_or_create_agent_worktree(workspace_dir: Path, agent_id: str) -> Path:
    """
    Ensures workspace_dir has an active, isolated Git worktree for agent_id on branch feature/{agent_id}.
    Returns the resolved Path to the agent's isolated worktree directory.
    """
    clean_agent = (agent_id or "agent").lower().replace(" ", "-").replace("@", "")
    workspace_dir = Path(workspace_dir).resolve()

    with _worktree_lock:
        ensure_git_repo(workspace_dir)

        worktree_base = workspace_dir / "worktrees"
        worktree_base.mkdir(parents=True, exist_ok=True)
        agent_wt_dir = (worktree_base / clean_agent).resolve()

        # Check if worktree directory already exists and is healthy
        if agent_wt_dir.exists():
            check = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(agent_wt_dir),
                capture_output=True,
                text=True
            )
            if check.returncode == 0 and check.stdout.strip() == "true":
                return agent_wt_dir
            else:
                # Broken or orphaned worktree directory, prune it
                subprocess.run(["git", "worktree", "prune"], cwd=str(workspace_dir), capture_output=True, text=True)

        branch_name = f"feature/{clean_agent}"

        # Create new worktree with branch
        cmd = ["git", "worktree", "add", "-B", branch_name, str(agent_wt_dir), "main"]
        res = subprocess.run(cmd, cwd=str(workspace_dir), capture_output=True, text=True)
        if res.returncode != 0:
            # If branch already exists, try checking it out directly
            fallback_cmd = ["git", "worktree", "add", str(agent_wt_dir), branch_name]
            res_fb = subprocess.run(fallback_cmd, cwd=str(workspace_dir), capture_output=True, text=True)
            if res_fb.returncode != 0:
                raise RuntimeError(f"Failed to create git worktree for {clean_agent}: {res.stderr}\n{res_fb.stderr}")

        # Configure local worktree git identity
        subprocess.run(["git", "config", "user.name", f"Agent {clean_agent.capitalize()}"], cwd=str(agent_wt_dir), capture_output=True, text=True)
        subprocess.run(["git", "config", "user.email", f"{clean_agent}@bridge-deck.internal"], cwd=str(agent_wt_dir), capture_output=True, text=True)

        return agent_wt_dir


def list_agent_worktrees(workspace_dir: Path) -> List[Dict[str, Any]]:
    """
    Returns a list of active git worktrees in the workspace.
    """
    workspace_dir = Path(workspace_dir).resolve()
    if not (workspace_dir / ".git").exists():
        return []

    res = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=str(workspace_dir),
        capture_output=True,
        text=True
    )
    if res.returncode != 0:
        return []

    worktrees = []
    current_entry: Dict[str, str] = {}
    for line in res.stdout.splitlines():
        line = line.strip()
        if not line:
            if current_entry:
                worktrees.append(current_entry)
                current_entry = {}
            continue
        if line.startswith("worktree "):
            current_entry["path"] = line.split(" ", 1)[1]
        elif line.startswith("HEAD "):
            current_entry["commit"] = line.split(" ", 1)[1]
        elif line.startswith("branch "):
            current_entry["branch"] = line.split(" ", 1)[1]

    if current_entry:
        worktrees.append(current_entry)

    return worktrees
