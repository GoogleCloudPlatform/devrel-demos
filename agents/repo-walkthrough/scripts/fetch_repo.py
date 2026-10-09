#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Universal repository analyzer for Repo Walkthrough.

Supports three ways of fetching a repository:
1. Local directory path (zero network calls)
2. Public GitHub repository without `gh` CLI:
   - Accepts `owner/repo` or `https://github.com/owner/repo`
   - Fetches repo metadata + recursive tree in 2 calls via `api.github.com`
   - Fetches raw source files via `raw.githubusercontent.com` (CDN, does not count
     against GitHub's 60 req/hr unauthenticated REST API quota)
3. Private (or authenticated) GitHub repository via `gh` CLI:
   - Uses `gh api` with the user's authenticated GitHub session (5,000 req/hr + private repo access)

Outputs ranked architectural candidate files, line counts, symbols, and suggested 5-layer
buckets to help an agent craft a high-signal 12-18 node `data.js` walkthrough.
"""

from __future__ import annotations

import argparse
import ast
import base64
import json
import os
import pathlib
import re
import shutil
import subprocess
import urllib.request
from typing import Any


CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".mjs", ".go", ".rs", ".swift",
    ".java", ".kt", ".rb", ".c", ".cc", ".cpp", ".h", ".cs",
    ".html", ".css", ".sh", ".sql", ".tf", ".yaml", ".yml",
    ".ipynb", ".toml", ".json", ".md",
}

CODE_FILENAMES = {
    "dockerfile",
    "makefile",
    "cloudbuild.yaml",
    "cloudbuild.yml",
}

SKIP_SUBSTRINGS = (
    "node_modules/",
    "vendor/",
    "dist/",
    "build/",
    ".next/",
    "target/",
    "tests/",
    "test/",
    "__tests__/",
    "test_",
    "_test.",
    ".spec.",
    ".test.",
    "examples/",
    "samples/",
    "migrations/",
    "/_compat.py",
    ".min.js",
    ".d.ts",
    "package-lock.json",
    "manifest.json",
)


def parse_github_target(target: str) -> tuple[str, str | None, str]:
  """Parse GitHub target into (owner/repo, branch_or_none, subpath_prefix)."""
  s = target.strip()
  m = re.match(
      r"^https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?(?:/(?:tree|blob)/([^/#?]+)(?:/([^#?]*))?)?/?$",
      s,
  )
  if m:
    repo = m.group(1)
    branch = m.group(2) or None
    subpath = (m.group(3) or "").strip("/")
    return repo, branch, subpath
  return normalize_repo_target(s), None, ""


def normalize_repo_target(target: str) -> str:
  """Normalize https://github.com/owner/repo(.git) into owner/repo if applicable."""
  m = re.match(r"^https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?(?:/.*)?$", target.strip())
  if m:
    return m.group(1)
  return target.strip()


def has_gh_cli() -> bool:
  if not shutil.which("gh"):
    return False
  try:
    subprocess.run(
        ["gh", "auth", "status"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )
    return True
  except subprocess.CalledProcessError:
    return False


def score_file_path(path: str, size_bytes: int = 0) -> float:
  """Heuristic score ranking files by architectural centrality across the 5 layers."""
  p_lower = path.lower()
  name = pathlib.Path(path).name.lower()
  parts = pathlib.Path(path).parts
  depth = len(parts)

  score = 50.0 - min(depth * 3.5, 25.0)

  # High-signal architectural filenames
  if name in ("__init__.py", "index.html", "index.ts", "index.js", "main.py", "main.go", "main.rs", "lib.rs", "mod.rs", "app.py", "server.py", "skill.md", "plugin.json", "dockerfile"):
    score += 25.0
  if any(k in p_lower for k in ("cli", "server", "api", "fast_api", "router", "handler", "entry", "skill", "plugin", "frontend", "ui", "web")):
    score += 18.0
  if any(k in p_lower for k in ("runner", "engine", "workflow", "orchestrat", "dispatch", "context", "runtime", "executor", "build_", "fetch_")):
    score += 20.0
  if any(k in p_lower for k in ("agent", "controller", "service", "core", "domain", "manager", "model", "client", "index.html", "data", "bigquery", "vertex", "gemini", "multimodal")):
    score += 16.0
  if any(k in p_lower for k in ("flow", "event", "pipeline", "stream", "state", "session", "bus", "hook", "audio", "render", "query", "search", "embed")):
    score += 16.0
  if any(k in p_lower for k in ("tool", "plugin", "adapter", "storage", "db", "eval", "memory", "llm", "schema", "sql", "terraform", "setup")):
    score += 14.0

  # Penalize trivial or overly huge generated files
  if 0 < size_bytes < 120 and name != "__init__.py":
    score -= 20.0
  elif size_bytes > 500_000:
    score -= 15.0

  return score


def guess_layer(path: str) -> str:
  """Suggest one of the 5 standard architectural layers based on path keywords."""
  p = path.lower()
  name = pathlib.Path(path).name.lower()
  if name in ("__init__.py", "index.ts", "index.js", "main.py", "main.go", "lib.rs", "app.py", "index.html") or any(
      k in p for k in ("cli", "cmd/", "api/", "fast_api", "server", "http", "routes", "frontend", "ui/")
  ):
    return "entry"
  if any(k in p for k in ("runner", "engine", "workflow", "orchestrat", "invocation", "runtime", "executor", "scheduler")):
    return "engine"
  if any(k in p for k in ("agent", "domain", "controller", "core", "entity", "hierarchy", "service", "model")):
    return "agents"
  if any(k in p for k in ("flow", "event", "pipeline", "stream", "bus", "middleware", "processor", "step", "query", "search")):
    return "flows"
  return "capabilities"


def filter_and_rank_paths(
    entries: list[tuple[str, int]],
    max_files: int,
) -> list[str]:
  scored: list[tuple[float, str]] = []
  for path, size in entries:
    name_lower = pathlib.Path(path).name.lower()
    ext = pathlib.Path(path).suffix.lower()
    if ext not in CODE_EXTENSIONS and name_lower not in CODE_FILENAMES:
      continue
    if any(skip in path for skip in SKIP_SUBSTRINGS):
      continue
    scored.append((score_file_path(path, size), path))
  scored.sort(key=lambda item: (-item[0], item[1]))
  return [p for _, p in scored[:max_files]]


def _scope_blobs(
    tree_items: list[dict[str, Any]],
    subpath: str = "",
) -> list[tuple[str, int]]:
  prefix = f"{subpath.strip('/')}/" if subpath.strip("/") else ""
  blobs: list[tuple[str, int]] = []
  for item in tree_items:
    if item.get("type") != "blob":
      continue
    full_path = item["path"]
    if prefix:
      if not full_path.startswith(prefix):
        continue
      rel_path = full_path[len(prefix):]
    else:
      rel_path = full_path
    if not rel_path:
      continue
    blobs.append((rel_path, int(item.get("size", 0))))
  return blobs


def fetch_github_public(
    repo: str,
    max_files: int = 24,
    branch_override: str | None = None,
    subpath: str = "",
) -> dict[str, Any]:
  """Fetch a public GitHub repo using unauthenticated REST + raw.githubusercontent.com."""
  headers = {"User-Agent": "repo-walkthrough/1.0"}
  req = urllib.request.Request(f"https://api.github.com/repos/{repo}", headers=headers)
  with urllib.request.urlopen(req, timeout=15) as resp:
    meta = json.loads(resp.read().decode("utf-8"))

  branch = branch_override or meta.get("default_branch", "main")
  tree_url = f"https://api.github.com/repos/{repo}/git/trees/{branch}?recursive=1"
  req_tree = urllib.request.Request(tree_url, headers=headers)
  with urllib.request.urlopen(req_tree, timeout=20) as resp:
    tree_data = json.loads(resp.read().decode("utf-8"))

  blobs = _scope_blobs(tree_data.get("tree", []), subpath=subpath)
  selected = filter_and_rank_paths(blobs, max_files)

  prefix = f"{subpath.strip('/')}/" if subpath.strip("/") else ""
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    full_path = f"{prefix}{rel_path}"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/{full_path}"
    try:
      r = urllib.request.Request(raw_url, headers=headers)
      with urllib.request.urlopen(r, timeout=10) as f_resp:
        file_contents[rel_path] = f_resp.read().decode("utf-8", errors="replace")
    except Exception:
      file_contents[rel_path] = ""

  return {
      "repo": repo,
      "subpath": subpath,
      "branch": branch,
      "description": meta.get("description") or f"GitHub repository {repo}",
      "stars": str(meta.get("stargazers_count", 0)),
      "language": meta.get("language") or "Code",
      "total_files": len(blobs),
      "all_paths": [p for p, _ in blobs],
      "files": file_contents,
  }


def fetch_github_via_gh(
    repo: str,
    max_files: int = 24,
    branch_override: str | None = None,
    subpath: str = "",
) -> dict[str, Any]:
  """Fetch a private or public GitHub repo using authenticated `gh api`."""
  meta_raw = subprocess.check_output(
      ["gh", "api", f"repos/{repo}"], text=True
  )
  meta = json.loads(meta_raw)
  branch = branch_override or meta.get("default_branch", "main")

  tree_raw = subprocess.check_output(
      ["gh", "api", f"repos/{repo}/git/trees/{branch}?recursive=1"], text=True
  )
  tree_data = json.loads(tree_raw)

  blobs = _scope_blobs(tree_data.get("tree", []), subpath=subpath)
  selected = filter_and_rank_paths(blobs, max_files)

  prefix = f"{subpath.strip('/')}/" if subpath.strip("/") else ""
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    full_path = f"{prefix}{rel_path}"
    try:
      b64 = subprocess.check_output(
          ["gh", "api", f"repos/{repo}/contents/{full_path}?ref={branch}", "--jq", ".content"],
          text=True,
      )
      file_contents[rel_path] = base64.b64decode(b64).decode("utf-8", errors="replace")
    except Exception:
      file_contents[rel_path] = ""

  return {
      "repo": repo,
      "subpath": subpath,
      "branch": branch,
      "description": meta.get("description") or f"GitHub repository {repo}",
      "stars": str(meta.get("stargazers_count", 0)),
      "language": meta.get("language") or "Code",
      "total_files": len(blobs),
      "all_paths": [p for p, _ in blobs],
      "files": file_contents,
  }


def fetch_local_dir(
    local_path: pathlib.Path,
    max_files: int = 24,
) -> dict[str, Any]:
  """Analyze a local directory without any network requests."""
  local_path = local_path.resolve()
  all_entries: list[tuple[str, int]] = []
  for root, dirs, filenames in os.walk(local_path):
    dirs[:] = [
        d for d in dirs
        if not d.startswith(".") and d not in ("node_modules", "__pycache__", "venv", ".venv", "dist", "build", "target")
    ]
    for fn in filenames:
      p = pathlib.Path(root) / fn
      rel = p.relative_to(local_path).as_posix()
      if p.suffix.lower() in CODE_EXTENSIONS or p.name.lower() in CODE_FILENAMES:
        try:
          sz = p.stat().st_size
        except OSError:
          sz = 0
        all_entries.append((rel, sz))

  selected = filter_and_rank_paths(all_entries, max_files)
  file_contents = {}
  for rel in selected:
    try:
      file_contents[rel] = (local_path / rel).read_text(encoding="utf-8", errors="replace")
    except Exception:
      file_contents[rel] = ""

  return {
      "repo": local_path.name,
      "subpath": "",
      "branch": "main",
      "description": f"Local repository at {local_path}",
      "stars": "Local",
      "language": "Code",
      "total_files": len(all_entries),
      "all_paths": [p for p, _ in all_entries],
      "files": file_contents,
  }


def parse_file_metadata(path: str, source: str) -> dict[str, Any]:
  """Extract line count, docstring/header summary, top symbols, and a concise code snippet."""
  if path.endswith(".ipynb"):
    try:
      nb = json.loads(source)
      code_lines: list[str] = []
      for cell in nb.get("cells", []):
        if cell.get("cell_type") == "code":
          cell_src = cell.get("source", [])
          if isinstance(cell_src, list):
            code_lines.extend("".join(cell_src).splitlines())
          elif isinstance(cell_src, str):
            code_lines.extend(cell_src.splitlines())
      source = "\n".join(code_lines)
    except Exception:
      pass

  lines = source.splitlines()
  line_count = len(lines)
  doc = ""
  symbols: list[dict[str, Any]] = []

  if path.endswith((".py", ".ipynb")):
    try:
      tree = ast.parse(source)
      raw_doc = ast.get_docstring(tree)
      if raw_doc:
        doc = raw_doc.strip().splitlines()[0]
      for node in tree.body:
        if isinstance(node, ast.ClassDef):
          cdoc = (ast.get_docstring(node) or "").strip().splitlines()
          summary = cdoc[0] if cdoc else f"Class {node.name}"
          symbols.append({"name": node.name, "line": node.lineno, "desc": summary})
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
          fdoc = (ast.get_docstring(node) or "").strip().splitlines()
          summary = fdoc[0] if fdoc else f"Function {node.name}()"
          symbols.append({"name": f"{node.name}()", "line": node.lineno, "desc": summary})
    except SyntaxError:
      pass
  else:
    for i, line in enumerate(lines[:60], start=1):
      s = line.strip()
      if not doc and s.startswith(("//", "/*", "*", "--")) and len(s.lstrip("/*- ")) > 12:
        doc = s.lstrip("/*- ").strip()
      m = re.match(
          r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:class|interface|type|function|func|struct|enum)\s+([A-Za-z0-9_]+)",
          s,
      )
      if m:
        symbols.append({"name": m.group(1), "line": i, "desc": s[:90]})

  non_comment = [
      l for l in lines
      if l.strip() and not l.strip().startswith(("#", "//", "/*", "*", "--"))
  ]
  snippet = "\n".join(non_comment[:10])[:420]

  return {
      "path": path,
      "label": pathlib.Path(path).name,
      "suggestedLayer": guess_layer(path),
      "lines": line_count,
      "doc": doc,
      "symbols": symbols[:6],
      "snippetPreview": snippet,
  }


def _extract_diff_preview(patch_text: str, max_lines: int = 16) -> str:
  """Extract a compact unified diff snippet (hunk headers + changed/context lines) for the inspector."""
  out: list[str] = []
  for line in patch_text.splitlines():
    if line.startswith(("diff --git", "index ", "--- ", "+++ ")):
      continue
    if line.startswith("@@") or line.startswith(("+", "-", " ")):
      out.append(line[:110])
      if len(out) >= max_lines:
        break
  return "\n".join(out)


def fetch_git_diff(
    local_path: pathlib.Path,
    diff_range: str,
    max_files: int = 24,
) -> dict[str, Any]:
  """Analyze files changed across a git diff range (e.g. '5984e02..HEAD' or 'HEAD~1..HEAD')."""
  local_path = local_path.resolve()
  try:
    numstat_out = subprocess.run(
        ["git", "-C", str(local_path), "diff", "--relative", "--numstat", diff_range, "--", "."],
        capture_output=True, text=True, check=True,
    ).stdout
    status_out = subprocess.run(
        ["git", "-C", str(local_path), "diff", "--relative", "--name-status", diff_range, "--", "."],
        capture_output=True, text=True, check=True,
    ).stdout
    commits_out = subprocess.run(
        ["git", "-C", str(local_path), "log", "--oneline", diff_range, "--", "."],
        capture_output=True, text=True, check=True,
    ).stdout
  except subprocess.CalledProcessError as e:
    raise RuntimeError(f"Git command failed: {e.stderr.strip() if e.stderr else e}") from e
  commits = [line.strip() for line in commits_out.splitlines() if line.strip()]

  status_by_path: dict[str, str] = {}
  for line in status_out.splitlines():
    parts = line.strip().split("\t")
    if len(parts) >= 2:
      code = parts[0][0].upper()
      rel_p = parts[-1]
      status_by_path[rel_p] = {
          "A": "added",
          "M": "modified",
          "D": "deleted",
          "R": "renamed",
      }.get(code, "modified")

  diff_Allowed = CODE_EXTENSIONS | {".md", ".json"}
  changed_entries: list[tuple[str, int]] = []
  file_diffs: dict[str, dict[str, Any]] = {}
  total_added = 0
  total_deleted = 0

  for line in numstat_out.splitlines():
    parts = line.strip().split("\t")
    if len(parts) < 3:
      continue
    add_s, del_s, rel_p = parts[0], parts[1], parts[-1]
    if add_s == "-" or del_s == "-":
      continue  # Skip binary files (.wav, .mp4, .png)
    p = pathlib.Path(rel_p)
    if p.suffix.lower() not in diff_Allowed and p.name.lower() not in CODE_FILENAMES:
      continue
    added = int(add_s)
    deleted = int(del_s)
    total_added += added
    total_deleted += deleted
    patch_raw = subprocess.check_output(
        ["git", "-C", str(local_path), "diff", "--relative", "-U2", diff_range, "--", rel_p],
        text=True,
    )
    preview = _extract_diff_preview(patch_raw)
    file_diffs[rel_p] = {
        "status": status_by_path.get(rel_p, "modified"),
        "added": added,
        "deleted": deleted,
        "patchPreview": preview,
    }
    full_file = local_path / rel_p
    sz = full_file.stat().st_size if full_file.exists() else (added + deleted) * 40
    changed_entries.append((rel_p, sz))

  # Rank changed files by number of lines changed first, then architectural path score
  changed_entries.sort(
      key=lambda item: (
          file_diffs[item[0]]["added"] + file_diffs[item[0]]["deleted"],
          score_file_path(item[0], item[1]),
      ),
      reverse=True,
  )
  selected = [p for p, _ in changed_entries[:max_files]]
  file_contents: dict[str, str] = {}
  for rel in selected:
    full_file = local_path / rel
    if full_file.exists():
      try:
        file_contents[rel] = full_file.read_text(encoding="utf-8", errors="replace")
      except Exception:
        file_contents[rel] = ""
    else:
      file_contents[rel] = file_diffs[rel].get("patchPreview", "")

  return {
      "repo": local_path.name,
      "subpath": "",
      "branch": diff_range,
      "diff_range": diff_range,
      "commits": commits,
      "diff_stats": {
          "changedFiles": len(changed_entries),
          "totalAdded": total_added,
          "totalDeleted": total_deleted,
      },
      "file_diffs": file_diffs,
      "description": (
          f"Git diff {diff_range} in {local_path.name} "
          f"({len(changed_entries)} files, +{total_added} / -{total_deleted})"
      ),
      "stars": f"+{total_added} / -{total_deleted}",
      "language": "Diff",
      "total_files": len(changed_entries),
      "all_paths": [p for p, _ in changed_entries],
      "files": file_contents,
  }


def build_analysis_report(info: dict[str, Any]) -> dict[str, Any]:
  file_diffs = info.get("file_diffs", {})
  analyzed = []
  for path, src in info["files"].items():
    meta = parse_file_metadata(path, src)
    if path in file_diffs:
      meta["diff"] = file_diffs[path]
      if file_diffs[path].get("patchPreview"):
        meta["snippetPreview"] = file_diffs[path]["patchPreview"]
    analyzed.append(meta)
  report = {
      "repo": info["repo"],
      "subpath": info.get("subpath", ""),
      "branch": info["branch"],
      "description": info["description"],
      "language": info["language"],
      "totalFiles": info["total_files"],
      "allPaths": info.get("all_paths", []),
      "analyzedCount": len(analyzed),
      "candidates": analyzed,
  }
  if info.get("diff_range"):
    report["diffRange"] = info["diff_range"]
    report["diffStats"] = info.get("diff_stats", {})
    report["commits"] = info.get("commits", [])
  return report


def export_voice_markdown(preset: dict[str, Any], out_path: pathlib.Path) -> None:
  """Export walkthrough narration into a markdown draft compatible with gemini-voice."""
  lines = [f"# {preset['title']} - Codebase Walkthrough\n"]
  lines.append(f"{preset.get('subtitle', '')}\n")
  for st in preset.get("walkthrough", []):
    lines.append(f"## Step {st['step']}: {st['title']}\n")
    lines.append(f"{st.get('narration') or st.get('summary', '')}\n")
    if st.get("takeaway"):
      lines.append(f"Key takeaway: {st['takeaway']}\n")
  out_path.write_text("\n".join(lines), encoding="utf-8")
  print(f"Wrote gemini-voice compatible markdown to: {out_path}")


def main() -> None:
  parser = argparse.ArgumentParser(description="Fetch and analyze any repository for Repo Walkthrough.")
  parser.add_argument(
      "target",
      nargs="?",
      default="google/adk-python",
      help="GitHub owner/repo, GitHub URL (including /tree/<branch>/<subpath>), or local directory path",
  )
  parser.add_argument(
      "--mode",
      choices=["auto", "public", "gh", "local"],
      default="auto",
      help="Fetch strategy: auto (default), public (HTTPS without gh), gh (gh CLI), or local",
  )
  parser.add_argument(
      "--diff",
      metavar="REV_RANGE",
      help="Analyze a git diff range in a local repository (e.g. 5984e02..HEAD or HEAD~1..HEAD)",
  )
  parser.add_argument(
      "--max-files",
      type=int,
      default=24,
      help="Maximum candidate files to fetch and rank (default: 24)",
  )
  parser.add_argument(
      "--json",
      metavar="JSON_PATH",
      help="Write structured candidate analysis JSON to the specified path",
  )
  parser.add_argument(
      "--export-voice",
      metavar="MARKDOWN_PATH",
      help="Export walkthrough narration as markdown for gemini-voice",
  )
  parser.add_argument(
      "--open",
      action="store_true",
      help="Open web/index.html in the default browser",
  )
  args = parser.parse_args()

  repo_root = pathlib.Path(__file__).resolve().parent.parent
  web_index = repo_root / "web" / "index.html"

  local_candidate = pathlib.Path(args.target).expanduser()
  norm_target, branch_override, subpath = parse_github_target(args.target)
  scope_label = f"{norm_target}/{subpath}" if subpath else norm_target

  if args.diff:
    print(f"[git-diff] Analyzing git diff {args.diff} at {local_candidate.resolve()}...")
    info = fetch_git_diff(local_candidate, diff_range=args.diff, max_files=args.max_files)
  elif args.mode == "local" or local_candidate.exists():
    print(f"[local] Analyzing local repository at {local_candidate.resolve()}...")
    info = fetch_local_dir(local_candidate, max_files=args.max_files)
  elif args.mode == "public" or (args.mode == "auto" and not has_gh_cli()):
    print(f"[public-https] Fetching {scope_label} via api.github.com + raw.githubusercontent.com (no gh CLI needed)...")
    info = fetch_github_public(
        norm_target,
        max_files=args.max_files,
        branch_override=branch_override,
        subpath=subpath,
    )
  else:
    print(f"[gh-cli] Fetching {scope_label} via authenticated gh CLI...")
    try:
      info = fetch_github_via_gh(
          norm_target,
          max_files=args.max_files,
          branch_override=branch_override,
          subpath=subpath,
      )
    except Exception:
      print(f"[fallback] Falling back to public HTTPS for {scope_label}...")
      info = fetch_github_public(
          norm_target,
          max_files=args.max_files,
          branch_override=branch_override,
          subpath=subpath,
      )

  report = build_analysis_report(info)
  print(
      f"Fetched {scope_label} ({report['totalFiles']} total code files, "
      f"{report['analyzedCount']} top architectural files analyzed)."
  )
  for c in report["candidates"][:18]:
    syms = ", ".join(s["name"] for s in c["symbols"][:4])
    sym_str = f" [{syms}]" if syms else ""
    diff_str = f" (+{c['diff']['added']} / -{c['diff']['deleted']})" if "diff" in c else ""
    print(f"  • [{c['suggestedLayer']:<12}] {c['path']} ({c['lines']} lines){diff_str}{sym_str}")

  if args.json:
    json_path = pathlib.Path(args.json).expanduser()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved structured analysis JSON to: {json_path}")

  if args.export_voice:
    out_md = pathlib.Path(args.export_voice).expanduser()
    preset = {
        "title": scope_label,
        "subtitle": report["description"],
        "walkthrough": [
            {
                "step": i + 1,
                "title": c["path"],
                "narration": f"Step {i + 1} covers {c['label']}, containing {c['lines']} lines of code.",
                "takeaway": c["doc"],
            }
            for i, c in enumerate(report["candidates"][:8])
        ],
    }
    export_voice_markdown(preset, out_md)

  if args.open:
    subprocess.run(["open", str(web_index)], check=False)


if __name__ == "__main__":
  main()
