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
   - Fetches raw source files via `raw.githubusercontent.com` (CDN, does not
     count against GitHub's 60 req/hr unauthenticated REST API quota)
3. Private (or authenticated) GitHub repository via `gh` CLI:
   - Uses `gh api` with the user's authenticated GitHub session (5,000 req/hr
     plus private repo access)

Outputs ranked architectural candidate files, line counts, symbols, and
suggested 5-layer buckets to help an agent craft a high-signal 12-18 node
`data.js` walkthrough.
"""

from __future__ import annotations

import argparse
import ast
import base64
from collections.abc import Callable, Mapping, Sequence
from http import client as http_client
import json
import ntpath
import os
import pathlib
import posixpath
import re
import shutil
import subprocess
import sys
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

CODE_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".go",
    ".rs",
    ".swift",
    ".java",
    ".kt",
    ".rb",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".cs",
    ".html",
    ".tmpl",
    ".css",
    ".sh",
    ".sql",
    ".tf",
    ".yaml",
    ".yml",
    ".ipynb",
    ".toml",
    ".json",
    ".md",
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

_HIGH_SIGNAL_FILENAMES = frozenset({
    "__init__.py",
    "index.html",
    "index.tmpl",
    "index.ts",
    "index.js",
    "main.py",
    "main.go",
    "main.rs",
    "lib.rs",
    "mod.rs",
    "app.py",
    "server.py",
    "skill.md",
    "plugin.json",
    "dockerfile",
})

_SCORE_KEYWORD_BUCKETS: tuple[tuple[tuple[str, ...], float], ...] = (
    (
        (
            "cli",
            "server",
            "api",
            "fast_api",
            "router",
            "handler",
            "entry",
            "skill",
            "plugin",
            "frontend",
            "ui",
            "web",
        ),
        18.0,
    ),
    (
        (
            "runner",
            "engine",
            "workflow",
            "orchestrat",
            "dispatch",
            "context",
            "runtime",
            "executor",
            "build_",
            "fetch_",
        ),
        20.0,
    ),
    (
        (
            "agent",
            "controller",
            "service",
            "core",
            "domain",
            "manager",
            "model",
            "client",
            "index.html",
            "index.tmpl",
            "data",
            "bigquery",
            "vertex",
            "gemini",
            "multimodal",
        ),
        16.0,
    ),
    (
        (
            "flow",
            "event",
            "pipeline",
            "stream",
            "state",
            "session",
            "bus",
            "hook",
            "audio",
            "render",
            "query",
            "search",
            "embed",
        ),
        16.0,
    ),
    (
        (
            "tool",
            "plugin",
            "adapter",
            "storage",
            "db",
            "eval",
            "memory",
            "llm",
            "schema",
            "sql",
            "terraform",
            "setup",
        ),
        14.0,
    ),
)

_ENTRY_FILENAMES = frozenset({
    "__init__.py",
    "index.ts",
    "index.js",
    "main.py",
    "main.go",
    "lib.rs",
    "app.py",
    "index.html",
    "index.tmpl",
})

_ENTRY_KEYWORDS = (
    "cli",
    "cmd/",
    "api/",
    "fast_api",
    "server",
    "http",
    "routes",
    "frontend",
    "ui/",
)
_ENGINE_KEYWORDS = (
    "runner",
    "engine",
    "workflow",
    "orchestrat",
    "invocation",
    "runtime",
    "executor",
    "scheduler",
)
_AGENTS_KEYWORDS = (
    "agent",
    "domain",
    "controller",
    "core",
    "entity",
    "hierarchy",
    "service",
    "model",
)
_FLOWS_KEYWORDS = (
    "flow",
    "event",
    "pipeline",
    "stream",
    "bus",
    "middleware",
    "processor",
    "step",
    "query",
    "search",
)

_SKIP_WALK_DIRS = frozenset({
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    "dist",
    "build",
    "target",
})

_GITHUB_TARGET_PATTERN = re.compile(
    r"https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?"
    r"(?:/(?:tree|blob)/([^/#?]+)(?:/([^#?]*))?)?/?"
)
_GITHUB_REPO_PATTERN = re.compile(
    r"https?://github\.com/([^/]+/[^/#?]+?)(?:\.git)?(?:/.*)?"
)
_VALID_REPO_SLUG_PATTERN = re.compile(
    r"^(?![.]{1,2}/)[A-Za-z0-9_.-]+/(?![.]{1,2}$)[A-Za-z0-9_.-]+$"
)
_SYMBOL_DECL_PATTERN = re.compile(
    r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?"
    r"(?:class|interface|type|function|func|struct|enum)\s+([A-Za-z0-9_]+)"
)
_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if sys.platform.startswith("win") and not os.environ.get(
    "NoDefaultCurrentDirectoryInExePath"
):
  os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"


def _is_abs_search_dir(entry: str, platform: str) -> bool:
  """Returns True when `entry` is an absolute path on `platform`."""
  if not entry or entry == ".":
    return False
  if platform.startswith("win"):
    return bool(ntpath.splitdrive(entry)[0]) and ntpath.isabs(entry)
  return posixpath.isabs(entry)


def _clean_search_path(
    raw_path: str | None,
    platform: str | None = None,
) -> list[str]:
  """Strips empty, '.', and relative entries from a PATH string."""
  active_platform = sys.platform if platform is None else platform
  if not raw_path:
    return []
  sep = ";" if active_platform.startswith("win") else os.pathsep
  dirs: list[str] = []
  for raw_entry in raw_path.split(sep):
    entry = (
        raw_entry.strip().strip('"')
        if active_platform.startswith("win")
        else raw_entry
    )
    if _is_abs_search_dir(entry, active_platform):
      dirs.append(entry)
  return dirs


def _resolve_executable(
    name: str,
    platform: str | None = None,
) -> str | None:
  """Resolves `name` to an absolute executable path without searching cwd."""
  active_platform = sys.platform if platform is None else platform
  if active_platform.startswith("win") and not os.environ.get(
      "NoDefaultCurrentDirectoryInExePath"
  ):
    os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"
  raw_path = os.environ["PATH"] if "PATH" in os.environ else os.defpath
  safe_dirs = _clean_search_path(raw_path, active_platform)
  if not safe_dirs:
    return None
  is_win = active_platform.startswith("win")
  path_mod = ntpath if is_win else posixpath
  norm = (
      (lambda p: ntpath.normcase(ntpath.normpath(p)))
      if is_win
      else posixpath.normpath
  )
  allowed_parents = {norm(directory) for directory in safe_dirs}

  def _is_allowed_hit(candidate: str | None) -> bool:
    return (
        bool(candidate)
        and _is_abs_search_dir(candidate, active_platform)
        and norm(path_mod.dirname(candidate)) in allowed_parents
    )

  sep = ";" if is_win else os.pathsep
  resolved = shutil.which(name, path=sep.join(safe_dirs))
  if _is_allowed_hit(resolved):
    return resolved
  if resolved:
    for directory in safe_dirs:
      fallback = shutil.which(path_mod.join(directory, name))
      if _is_allowed_hit(fallback):
        return fallback
  return None


def _safe_subprocess_kwargs(platform: str | None = None) -> dict[str, Any]:
  """Returns `cwd` and `env` kwargs isolating child spawns from untrusted cwd."""
  active_platform = sys.platform if platform is None else platform
  kwargs: dict[str, Any] = {"cwd": _SCRIPT_DIR}
  if active_platform.startswith("win"):
    child_env = dict(os.environ)
    child_env["NoDefaultCurrentDirectoryInExePath"] = "1"
    kwargs["env"] = child_env
  return kwargs


def _windows_rundll32_path() -> str:
  """Returns `%SystemRoot%\\System32\\rundll32.exe` using an absolute root."""
  raw_root = (
      os.environ.get("SystemRoot")
      or os.environ.get("SYSTEMROOT")
      or os.environ.get("windir")
      or os.environ.get("WINDIR")
      or r"C:\Windows"
  )
  cleaned_root = raw_root.strip().strip('"')
  if not _is_abs_search_dir(cleaned_root, "win32"):
    cleaned_root = r"C:\Windows"
  return ntpath.join(cleaned_root, "System32", "rundll32.exe")


def _is_plugin_or_repo_root(candidate: pathlib.Path) -> bool:
  """Returns True when `candidate` is the plugin or repository root."""
  web_dir = candidate / "web"
  return (
      (candidate / "plugin.json").exists()
      or (web_dir / "index.html").exists()
      or (web_dir / "index.tmpl").exists()
      or (web_dir / "data-adk.js").exists()
  )


def _is_within_root(target: pathlib.Path, root: pathlib.Path) -> bool:
  """Returns True if `target` resolves inside `root` (blocks external symlinks)."""
  try:
    return target.resolve().is_relative_to(root.resolve())
  except (OSError, ValueError):
    return False


def _validate_repo_slug(repo: str) -> str:
  """Validates a GitHub `owner/repo` slug before building API URLs."""
  cleaned = repo.strip()
  if not _VALID_REPO_SLUG_PATTERN.fullmatch(cleaned):
    raise ValueError(f"Invalid GitHub owner/repo identifier: {repo!r}")
  return cleaned


def _validate_diff_range(diff_range: str) -> str:
  """Validates `diff_range` to prevent git option injection."""
  cleaned = diff_range.strip()
  if not cleaned or cleaned.startswith("-"):
    raise ValueError(f"Invalid git diff range: {diff_range!r}")
  if any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
    raise ValueError(f"Invalid control character in git diff range: {diff_range!r}")
  for endpoint in re.split(r"\.{2,3}", cleaned):
    if endpoint.startswith("-"):
      raise ValueError(f"Invalid revision endpoint in git diff range: {diff_range!r}")
  return cleaned


def resolve_repo_root(script_dir: pathlib.Path | None = None) -> pathlib.Path:
  """Resolves the plugin or skill root from `scripts/` or skill subdirectories.

  Args:
    script_dir: Directory containing the script. When `None`, resolves from this
      file's parent directory.

  Returns:
    The resolved plugin root directory when `plugin.json` or `web/` is present,
    or the immediate skill parent directory for standalone skill installs.
  """
  base = (script_dir or pathlib.Path(__file__).resolve().parent).resolve()
  plugin_candidate = base.parent.parent.parent
  direct_candidate = base.parent
  if _is_plugin_or_repo_root(plugin_candidate):
    return plugin_candidate
  if _is_plugin_or_repo_root(direct_candidate):
    return direct_candidate
  return direct_candidate


def resolve_web_index(repo_root: pathlib.Path) -> pathlib.Path | None:
  """Resolves a built `.html` viewer page without ever falling back to `.tmpl`.

  Args:
    repo_root: Repository, plugin, or skill root directory.

  Returns:
    Path to a built `index.html` file if one exists on disk, or `None` when no
    end-product HTML file has been built yet.
  """
  for candidate in (
      repo_root / "web" / "index.html",
      repo_root / "examples" / "self-walkthrough" / "index.html",
  ):
    if candidate.exists():
      return candidate
  return None


def open_target(
    target_path: pathlib.Path,
    platform: str | None = None,
    runner: Callable[..., Any] = subprocess.run,
    startfile_fn: Callable[[str], Any] | None = None,
) -> bool:
  """Opens a built HTML or media file in the default viewer safely.

  Never opens raw `.tmpl` template files or invokes `cmd.exe /c start`.

  Args:
    target_path: Local built HTML or media path to open.
    platform: Platform identifier such as `darwin`, `win32`, or `linux`.
    runner: Subprocess execution callable accepting a command sequence.
    startfile_fn: Optional `os.startfile` override for Windows testing.

  Returns:
    True if the launcher was invoked cleanly, or False on `.tmpl` or OS errors.
  """
  if target_path.suffix.lower() == ".tmpl":
    return False
  active_platform = sys.platform if platform is None else platform
  exec_kwargs = _safe_subprocess_kwargs(active_platform)
  try:
    if active_platform == "darwin":
      open_exe = _resolve_executable("open", active_platform) or "/usr/bin/open"
      runner([open_exe, str(target_path)], check=False, **exec_kwargs)
    elif active_platform.startswith("win"):
      opener = startfile_fn or getattr(os, "startfile", None)
      if opener is not None and runner is subprocess.run:
        opener(str(target_path))
      elif startfile_fn is not None:
        startfile_fn(str(target_path))
      else:
        runner(
            [
                _windows_rundll32_path(),
                "url.dll,FileProtocolHandler",
                str(target_path),
            ],
            check=False,
            **exec_kwargs,
        )
    else:
      xdg_exe = _resolve_executable("xdg-open", active_platform)
      if xdg_exe is None and runner is subprocess.run:
        raise FileNotFoundError("xdg-open")
      runner([xdg_exe or "xdg-open", str(target_path)], check=False, **exec_kwargs)
    return True
  except (OSError, subprocess.SubprocessError):
    print(
        "Could not auto-open browser in this environment. "
        f"Open manually: {target_path}"
    )
    return False


def parse_github_target(target: str) -> tuple[str, str | None, str]:
  """Parses a GitHub target into `(owner/repo, branch, subpath_prefix)`.

  Args:
    target: Raw GitHub URL, `owner/repo` slug, or local path string.

  Returns:
    A 3-tuple `(repo, branch, subpath)` where `branch` is `None` when the target
    does not include an explicit `/tree/<branch>` or `/blob/<branch>` segment.
  """
  cleaned = target.strip()
  match = _GITHUB_TARGET_PATTERN.fullmatch(cleaned)
  if match:
    repo = match.group(1)
    branch = match.group(2) or None
    subpath = (match.group(3) or "").strip("/")
    return repo, branch, subpath
  return normalize_repo_target(cleaned), None, ""


def normalize_repo_target(target: str) -> str:
  """Normalizes `https://github.com/owner/repo(.git)` into `owner/repo`."""
  cleaned = target.strip()
  match = _GITHUB_REPO_PATTERN.fullmatch(cleaned)
  if match:
    return match.group(1)
  return cleaned


def has_gh_cli() -> bool:
  """Returns True if the `gh` CLI is installed and authenticated."""
  gh_exe = _resolve_executable("gh")
  if not gh_exe:
    return False
  try:
    subprocess.run(
        [gh_exe, "auth", "status"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
        **_safe_subprocess_kwargs(),
    )
    return True
  except (OSError, subprocess.CalledProcessError):
    return False


def score_file_path(path: str, size_bytes: int = 0) -> float:
  """Computes a heuristic centrality score to rank candidate source files."""
  path_lower = path.lower()
  name_lower = pathlib.Path(path).name.lower()
  depth = len(pathlib.Path(path).parts)

  score = 50.0 - min(depth * 3.5, 25.0)
  if name_lower in _HIGH_SIGNAL_FILENAMES:
    score += 25.0
  for keywords, weight in _SCORE_KEYWORD_BUCKETS:
    if any(keyword in path_lower for keyword in keywords):
      score += weight

  if 0 < size_bytes < 120 and name_lower != "__init__.py":
    score -= 20.0
  elif size_bytes > 500_000:
    score -= 15.0

  return score


def guess_layer(path: str) -> str:
  """Suggests one of the 5 architectural layers based on path keywords."""
  path_lower = path.lower()
  name_lower = pathlib.Path(path).name.lower()
  if name_lower in _ENTRY_FILENAMES or any(
      keyword in path_lower for keyword in _ENTRY_KEYWORDS
  ):
    return "entry"
  if any(keyword in path_lower for keyword in _ENGINE_KEYWORDS):
    return "engine"
  if any(keyword in path_lower for keyword in _AGENTS_KEYWORDS):
    return "agents"
  if any(keyword in path_lower for keyword in _FLOWS_KEYWORDS):
    return "flows"
  return "capabilities"


def filter_and_rank_paths(
    entries: Sequence[tuple[str, int]],
    max_files: int,
) -> list[str]:
  """Filters non-source paths and returns the top-ranked relative file paths.

  Args:
    entries: Sequence of `(relative_path, size_bytes)` pairs.
    max_files: Maximum number of ranked file paths to return.

  Returns:
    Up to `max_files` relative file paths ordered by descending score.
  """
  scored: list[tuple[float, str]] = []
  for rel_path, size_bytes in entries:
    file_path = pathlib.Path(rel_path)
    name_lower = file_path.name.lower()
    ext = file_path.suffix.lower()
    if ext not in CODE_EXTENSIONS and name_lower not in CODE_FILENAMES:
      continue
    if any(skip in rel_path for skip in SKIP_SUBSTRINGS):
      continue
    scored.append((score_file_path(rel_path, size_bytes), rel_path))
  scored.sort(key=lambda item: (-item[0], item[1]))
  return [rel_path for _, rel_path in scored[:max_files]]


def _scope_blobs(
    tree_items: Sequence[Mapping[str, Any]],
    subpath: str = "",
) -> list[tuple[str, int]]:
  """Extracts `(relative_path, size_bytes)` blob entries scoped to `subpath`."""
  clean_subpath = subpath.strip("/")
  prefix = f"{clean_subpath}/" if clean_subpath else ""
  blobs: list[tuple[str, int]] = []
  for item in tree_items:
    if item.get("type") != "blob":
      continue
    full_path = str(item["path"])
    if prefix:
      if not full_path.startswith(prefix):
        continue
      rel_path = full_path[len(prefix) :]
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
  """Fetches a public GitHub repository via REST metadata and raw content CDN.

  Args:
    repo: GitHub `owner/repo` identifier.
    max_files: Maximum candidate files whose contents should be downloaded.
    branch_override: Explicit branch or tag ref. When `None`, uses the
      repository's `default_branch` (or `"main"`).
    subpath: Optional monorepo subdirectory prefix.

  Returns:
    Repository metadata, blob list, and downloaded file contents keyed by path.
  """
  repo = _validate_repo_slug(repo)
  headers = {"User-Agent": "repo-walkthrough/1.0"}
  meta_url = f"https://api.github.com/repos/{repo}"
  meta_req = urllib_request.Request(meta_url, headers=headers)
  with urllib_request.urlopen(meta_req, timeout=15) as response:
    meta = json.loads(response.read().decode("utf-8"))

  branch = branch_override or meta.get("default_branch", "main")
  encoded_branch = urllib_parse.quote(branch, safe="")
  tree_url = (
      f"https://api.github.com/repos/{repo}/git/trees/"
      f"{encoded_branch}?recursive=1"
  )
  tree_req = urllib_request.Request(tree_url, headers=headers)
  with urllib_request.urlopen(tree_req, timeout=20) as response:
    tree_data = json.loads(response.read().decode("utf-8"))

  blobs = _scope_blobs(tree_data.get("tree", []), subpath=subpath)
  selected = filter_and_rank_paths(blobs, max_files)

  clean_subpath = subpath.strip("/")
  prefix = f"{clean_subpath}/" if clean_subpath else ""
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    full_path = f"{prefix}{rel_path}"
    encoded_path = urllib_parse.quote(full_path)
    raw_url = (
        f"https://raw.githubusercontent.com/{repo}/"
        f"{encoded_branch}/{encoded_path}"
    )
    try:
      file_req = urllib_request.Request(raw_url, headers=headers)
      with urllib_request.urlopen(file_req, timeout=10) as file_response:
        file_contents[rel_path] = file_response.read().decode(
            "utf-8", errors="replace"
        )
    except (
        OSError,
        urllib_error.URLError,
        http_client.HTTPException,
        ValueError,
    ):
      file_contents[rel_path] = ""

  return {
      "repo": repo,
      "subpath": subpath,
      "branch": branch,
      "description": meta.get("description") or f"GitHub repository {repo}",
      "stars": str(meta.get("stargazers_count", 0)),
      "language": meta.get("language") or "Code",
      "total_files": len(blobs),
      "all_paths": [rel_path for rel_path, _ in blobs],
      "files": file_contents,
  }


def fetch_github_via_gh(
    repo: str,
    max_files: int = 24,
    branch_override: str | None = None,
    subpath: str = "",
) -> dict[str, Any]:
  """Fetches a private or public GitHub repository via authenticated `gh api`.

  Args:
    repo: GitHub `owner/repo` identifier.
    max_files: Maximum candidate files whose contents should be downloaded.
    branch_override: Explicit branch or tag ref. When `None`, uses the
      repository's `default_branch` (or `"main"`).
    subpath: Optional monorepo subdirectory prefix.

  Returns:
    Repository metadata, blob list, and decoded file contents keyed by path.
  """
  repo = _validate_repo_slug(repo)
  gh_exe = _resolve_executable("gh")
  if not gh_exe:
    raise FileNotFoundError("gh CLI executable not found on PATH.")
  exec_kwargs = _safe_subprocess_kwargs()
  meta_raw = subprocess.check_output(
      [gh_exe, "api", f"repos/{repo}"],
      encoding="utf-8",
      errors="replace",
      **exec_kwargs,
  )
  meta = json.loads(meta_raw)
  branch = branch_override or meta.get("default_branch", "main")
  encoded_branch = urllib_parse.quote(branch, safe="")

  tree_endpoint = f"repos/{repo}/git/trees/{encoded_branch}?recursive=1"
  tree_raw = subprocess.check_output(
      [gh_exe, "api", tree_endpoint],
      encoding="utf-8",
      errors="replace",
      **exec_kwargs,
  )
  tree_data = json.loads(tree_raw)

  blobs = _scope_blobs(tree_data.get("tree", []), subpath=subpath)
  selected = filter_and_rank_paths(blobs, max_files)

  clean_subpath = subpath.strip("/")
  prefix = f"{clean_subpath}/" if clean_subpath else ""
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    full_path = f"{prefix}{rel_path}"
    encoded_path = urllib_parse.quote(full_path)
    content_endpoint = (
        f"repos/{repo}/contents/{encoded_path}?ref={encoded_branch}"
    )
    try:
      b64_content = subprocess.check_output(
          [gh_exe, "api", content_endpoint, "--jq", ".content"],
          encoding="utf-8",
          errors="replace",
          **exec_kwargs,
      )
      file_contents[rel_path] = base64.b64decode(b64_content).decode(
          "utf-8", errors="replace"
      )
    except (OSError, subprocess.SubprocessError, ValueError):
      file_contents[rel_path] = ""

  return {
      "repo": repo,
      "subpath": subpath,
      "branch": branch,
      "description": meta.get("description") or f"GitHub repository {repo}",
      "stars": str(meta.get("stargazers_count", 0)),
      "language": meta.get("language") or "Code",
      "total_files": len(blobs),
      "all_paths": [rel_path for rel_path, _ in blobs],
      "files": file_contents,
  }


def fetch_local_dir(
    local_path: pathlib.Path,
    max_files: int = 24,
) -> dict[str, Any]:
  """Analyzes a local directory or single file without network requests.

  Args:
    local_path: Local filesystem directory or file path to inspect.
    max_files: Maximum candidate files whose contents should be loaded.

  Returns:
    Repository metadata, discovered file paths, and loaded file contents.

  Raises:
    FileNotFoundError: If `local_path` does not exist.
  """
  local_path = local_path.resolve()
  base_dir = local_path if local_path.is_dir() else local_path.parent
  all_entries: list[tuple[str, int]] = []
  if local_path.is_file():
    all_entries.append((local_path.name, local_path.stat().st_size))
  elif local_path.is_dir():
    for root, dirs, filenames in os.walk(local_path):
      dirs[:] = [
          dirname
          for dirname in dirs
          if not dirname.startswith(".") and dirname not in _SKIP_WALK_DIRS
      ]
      for filename in filenames:
        candidate_path = pathlib.Path(root) / filename
        if candidate_path.is_symlink() and not _is_within_root(
            candidate_path, local_path
        ):
          continue
        rel_path = candidate_path.relative_to(local_path).as_posix()
        is_code = (
            candidate_path.suffix.lower() in CODE_EXTENSIONS
            or candidate_path.name.lower() in CODE_FILENAMES
        )
        if is_code:
          try:
            size_bytes = candidate_path.stat().st_size
          except OSError:
            size_bytes = 0
          all_entries.append((rel_path, size_bytes))
  else:
    raise FileNotFoundError(f"Path not found: {local_path}")

  selected = filter_and_rank_paths(all_entries, max_files)
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    target_file = base_dir / rel_path
    if not _is_within_root(target_file, base_dir):
      continue
    try:
      file_contents[rel_path] = target_file.read_text(
          encoding="utf-8", errors="replace"
      )
    except OSError:
      file_contents[rel_path] = ""

  return {
      "repo": local_path.name,
      "subpath": "",
      "branch": "main",
      "description": f"Local repository at {local_path}",
      "stars": "Local",
      "language": "Code",
      "total_files": len(all_entries),
      "all_paths": [rel_path for rel_path, _ in all_entries],
      "files": file_contents,
  }


def _extract_notebook_source(raw_source: str) -> str:
  """Extracts concatenated code-cell text from an `.ipynb` JSON document."""
  try:
    notebook = json.loads(raw_source)
    code_lines: list[str] = []
    for cell in notebook.get("cells", []):
      if cell.get("cell_type") == "code":
        cell_src = cell.get("source", [])
        if isinstance(cell_src, list):
          code_lines.extend("".join(cell_src).splitlines())
        elif isinstance(cell_src, str):
          code_lines.extend(cell_src.splitlines())
    return "\n".join(code_lines)
  except (json.JSONDecodeError, TypeError, AttributeError):
    # Fall back to raw file text if the notebook JSON is malformed.
    return raw_source


def _extract_python_doc_and_symbols(
    source: str,
) -> tuple[str, list[dict[str, Any]]]:
  """Extracts the top-level docstring and public symbols from Python code."""
  doc = ""
  symbols: list[dict[str, Any]] = []
  try:
    tree = ast.parse(source)
  except SyntaxError:
    return doc, symbols

  raw_doc = ast.get_docstring(tree)
  if raw_doc:
    doc = raw_doc.strip().splitlines()[0]
  for node in tree.body:
    if isinstance(node, ast.ClassDef):
      class_doc = (ast.get_docstring(node) or "").strip().splitlines()
      summary = class_doc[0] if class_doc else f"Class {node.name}"
      symbols.append({"name": node.name, "line": node.lineno, "desc": summary})
    elif isinstance(
        node, (ast.FunctionDef, ast.AsyncFunctionDef)
    ) and not node.name.startswith("_"):
      func_doc = (ast.get_docstring(node) or "").strip().splitlines()
      summary = func_doc[0] if func_doc else f"Function {node.name}()"
      symbols.append(
          {"name": f"{node.name}()", "line": node.lineno, "desc": summary}
      )
  return doc, symbols


def parse_file_metadata(path: str, source: str) -> dict[str, Any]:
  """Extracts line count, header summary, top symbols, and a code snippet."""
  if path.endswith(".ipynb"):
    source = _extract_notebook_source(source)

  lines = source.splitlines()
  line_count = len(lines)
  doc = ""
  symbols: list[dict[str, Any]] = []

  if path.endswith((".py", ".ipynb")):
    doc, symbols = _extract_python_doc_and_symbols(source)
  else:
    for line_num, raw_line in enumerate(lines[:60], start=1):
      stripped = raw_line.strip()
      is_comment = stripped.startswith(("//", "/*", "*", "--"))
      if not doc and is_comment and len(stripped.lstrip("/*- ")) > 12:
        doc = stripped.lstrip("/*- ").strip()
      match = _SYMBOL_DECL_PATTERN.search(stripped)
      if match:
        symbols.append(
            {"name": match.group(1), "line": line_num, "desc": stripped[:90]}
        )

  comment_prefixes = ("#", "//", "/*", "*", "--")
  non_comment = [
      line
      for line in lines
      if line.strip() and not line.strip().startswith(comment_prefixes)
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
  """Extracts a compact unified diff snippet for the node inspector."""
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
  """Analyzes files changed across a git diff range such as `HEAD~1..HEAD`.

  Args:
    local_path: Local git repository directory (or subdirectory).
    diff_range: Git revision range passed to `git diff` and `git log`.
    max_files: Maximum changed candidate files to include in the report.

  Returns:
    Diff statistics, commit summaries, per-file patches, and file contents.

  Raises:
    ValueError: If `diff_range` starts with `-` or contains control characters.
    RuntimeError: If any underlying `git` command fails.
  """
  diff_range = _validate_diff_range(diff_range)
  git_exe = _resolve_executable("git")
  if not git_exe:
    raise RuntimeError("Git executable not found on PATH.")
  exec_kwargs = _safe_subprocess_kwargs()
  local_path = local_path.resolve()
  base_cmd = [git_exe, "-c", "core.quotePath=false", "-C", str(local_path)]
  diff_base = [*base_cmd, "diff", "--relative", "--no-renames"]
  effective_range = diff_range
  try:
    if "..." in diff_range:
      left_raw, right_raw = diff_range.split("...", 1)
      left_ref = left_raw or "HEAD"
      right_ref = right_raw or "HEAD"
      mb_out = subprocess.run(
          [*base_cmd, "merge-base", left_ref, right_ref],
          capture_output=True,
          encoding="utf-8",
          errors="replace",
          check=True,
          **exec_kwargs,
      ).stdout.strip()
      if mb_out:
        effective_range = f"{mb_out}..{right_ref}"

    numstat_out = subprocess.run(
        [*diff_base, "--numstat", effective_range, "--", "."],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        **exec_kwargs,
    ).stdout
    status_out = subprocess.run(
        [*diff_base, "--name-status", effective_range, "--", "."],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        **exec_kwargs,
    ).stdout
    commits_out = subprocess.run(
        [*base_cmd, "log", "--oneline", effective_range, "--", "."],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        **exec_kwargs,
    ).stdout
  except subprocess.CalledProcessError as err:
    detail = err.stderr.strip() if err.stderr else str(err)
    raise RuntimeError(f"Git command failed: {detail}") from err

  commits = [line.strip() for line in commits_out.splitlines() if line.strip()]
  status_map = {
      "A": "added",
      "M": "modified",
      "D": "deleted",
      "R": "renamed",
  }
  status_by_path: dict[str, str] = {}
  for line in status_out.splitlines():
    parts = line.strip().split("\t")
    if len(parts) >= 2:
      code = parts[0][0].upper()
      status_by_path[parts[-1]] = status_map.get(code, "modified")

  diff_allowed = CODE_EXTENSIONS | {".md", ".json"}
  changed_entries: list[tuple[str, int]] = []
  file_diffs: dict[str, dict[str, Any]] = {}
  total_added = 0
  total_deleted = 0

  for line in numstat_out.splitlines():
    parts = line.strip().split("\t")
    if len(parts) < 3:
      continue
    add_str, del_str, rel_path = parts[0], parts[1], parts[-1]
    if add_str == "-" or del_str == "-":
      continue  # Skip binary files (.wav, .mp4, .png).
    rel_file = pathlib.Path(rel_path)
    if (
        rel_file.suffix.lower() not in diff_allowed
        and rel_file.name.lower() not in CODE_FILENAMES
    ):
      continue
    if any(skip in rel_path for skip in SKIP_SUBSTRINGS):
      continue
    added = int(add_str)
    deleted = int(del_str)
    total_added += added
    total_deleted += deleted
    file_diffs[rel_path] = {
        "status": status_by_path.get(rel_path, "modified"),
        "added": added,
        "deleted": deleted,
        "patchPreview": "",
    }
    full_file = local_path / rel_path
    if full_file.exists() and _is_within_root(full_file, local_path):
      try:
        size_bytes = full_file.stat().st_size
      except OSError:
        size_bytes = (added + deleted) * 40
    else:
      size_bytes = (added + deleted) * 40
    changed_entries.append((rel_path, size_bytes))

  changed_entries.sort(
      key=lambda item: (
          file_diffs[item[0]]["added"] + file_diffs[item[0]]["deleted"],
          score_file_path(item[0], item[1]),
      ),
      reverse=True,
  )
  selected = [rel_path for rel_path, _ in changed_entries[:max_files]]
  file_contents: dict[str, str] = {}
  for rel_path in selected:
    patch_raw = subprocess.run(
        [
            *base_cmd,
            "diff",
            "--relative",
            "-U2",
            effective_range,
            "--",
            rel_path,
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        **exec_kwargs,
    ).stdout
    file_diffs[rel_path]["patchPreview"] = _extract_diff_preview(patch_raw)
    full_file = local_path / rel_path
    if full_file.exists() and _is_within_root(full_file, local_path):
      try:
        file_contents[rel_path] = full_file.read_text(
            encoding="utf-8", errors="replace"
        )
      except OSError:
        file_contents[rel_path] = ""
    else:
      file_contents[rel_path] = file_diffs[rel_path].get("patchPreview", "")

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
      "all_paths": [rel_path for rel_path, _ in changed_entries],
      "files": file_contents,
  }


def build_analysis_report(info: Mapping[str, Any]) -> dict[str, Any]:
  """Builds the structured JSON analysis report from fetched repository data."""
  file_diffs = info.get("file_diffs", {})
  analyzed: list[dict[str, Any]] = []
  for path, src in info["files"].items():
    meta = parse_file_metadata(path, src)
    diff_entry = file_diffs.get(path)
    if diff_entry is not None:
      meta["diff"] = diff_entry
      patch_preview = diff_entry.get("patchPreview")
      if patch_preview:
        meta["snippetPreview"] = patch_preview
    analyzed.append(meta)
  report: dict[str, Any] = {
      "repo": info["repo"],
      "subpath": info.get("subpath", ""),
      "branch": info["branch"],
      "description": info["description"],
      "language": info["language"],
      "totalFiles": info["total_files"],
      "allPaths": list(info.get("all_paths", [])),
      "analyzedCount": len(analyzed),
      "candidates": analyzed,
  }
  if info.get("diff_range"):
    report["diffRange"] = info["diff_range"]
    report["diffStats"] = info.get("diff_stats", {})
    report["commits"] = info.get("commits", [])
  return report


def export_voice_markdown(
    preset: Mapping[str, Any], out_path: pathlib.Path
) -> None:
  """Exports walkthrough narration into a spoken-friendly markdown draft."""
  lines = [f"# {preset['title']} - Codebase Walkthrough\n"]
  lines.append(f"{preset.get('subtitle', '')}\n")
  for step_item in preset.get("walkthrough", []):
    lines.append(f"## Step {step_item['step']}: {step_item['title']}\n")
    narration = step_item.get("narration") or step_item.get("summary", "")
    lines.append(f"{narration}\n")
    if step_item.get("takeaway"):
      lines.append(f"Key takeaway: {step_item['takeaway']}\n")
  out_path.write_text("\n".join(lines), encoding="utf-8")
  print(f"Wrote spoken walkthrough markdown to: {out_path}")


def _build_arg_parser() -> argparse.ArgumentParser:
  """Creates the command-line argument parser for `fetch_repo.py`."""
  parser = argparse.ArgumentParser(
      description="Fetch and analyze any repository for Repo Walkthrough."
  )
  parser.add_argument(
      "target",
      nargs="?",
      default="google/adk-python",
      help=(
          "GitHub owner/repo, GitHub URL (including /tree/<branch>/<subpath>), "
          "or local directory path"
      ),
  )
  parser.add_argument(
      "--mode",
      choices=["auto", "public", "gh", "local"],
      default="auto",
      help=(
          "Fetch strategy: auto (default), public (HTTPS without gh), "
          "gh (gh CLI), or local"
      ),
  )
  parser.add_argument(
      "--diff",
      metavar="REV_RANGE",
      help=(
          "Analyze a git diff range in a local repository "
          "(e.g. 5984e02..HEAD or HEAD~1..HEAD)"
      ),
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
      help="Export walkthrough narration as spoken-friendly markdown",
  )
  parser.add_argument(
      "--open",
      action="store_true",
      help="Open a built index.html viewer page if available",
  )
  return parser


def main(argv: Sequence[str] | None = None) -> None:
  """CLI entry point for fetching and analyzing a target repository.

  Args:
    argv: Optional CLI argument sequence. When `None`, parses `sys.argv[1:]`.
  """
  args = _build_arg_parser().parse_args(argv)
  repo_root = resolve_repo_root()
  web_index = resolve_web_index(repo_root)

  local_candidate = pathlib.Path(args.target).expanduser()
  norm_target, branch_override, subpath = parse_github_target(args.target)
  scope_label = f"{norm_target}/{subpath}" if subpath else norm_target

  if args.diff:
    resolved_dir = local_candidate.resolve()
    print(f"[git-diff] Analyzing git diff {args.diff} at {resolved_dir}...")
    info = fetch_git_diff(
        local_candidate, diff_range=args.diff, max_files=args.max_files
    )
  elif args.mode == "local" or (args.mode == "auto" and local_candidate.exists()):
    resolved_dir = local_candidate.resolve()
    print(f"[local] Analyzing local repository at {resolved_dir}...")
    info = fetch_local_dir(local_candidate, max_files=args.max_files)
  elif args.mode == "public" or (args.mode == "auto" and not has_gh_cli()):
    print(
        f"[public-https] Fetching {scope_label} via api.github.com + "
        "raw.githubusercontent.com (no gh CLI needed)..."
    )
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
    except (
        OSError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
        KeyError,
        ValueError,
    ):
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
  for candidate in report["candidates"][:18]:
    syms = ", ".join(sym["name"] for sym in candidate["symbols"][:4])
    sym_str = f" [{syms}]" if syms else ""
    diff_info = candidate.get("diff")
    diff_str = (
        f" (+{diff_info['added']} / -{diff_info['deleted']})"
        if diff_info
        else ""
    )
    layer = candidate["suggestedLayer"]
    print(
        f"  • [{layer:<12}] {candidate['path']} "
        f"({candidate['lines']} lines){diff_str}{sym_str}"
    )

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
                "step": idx + 1,
                "title": candidate["path"],
                "narration": (
                    f"Step {idx + 1} covers {candidate['label']}, "
                    f"containing {candidate['lines']} lines of code."
                ),
                "takeaway": candidate["doc"],
            }
            for idx, candidate in enumerate(report["candidates"][:8])
        ],
    }
    export_voice_markdown(preset, out_md)

  if args.open:
    if web_index is not None:
      open_target(web_index)
    else:
      print(
          "No built index.html found yet. Build the website first with "
          "'node skills/repo-walkthrough/scripts/build_walkthrough.mjs --data "
          "<path/to/data.js> --open'."
      )


if __name__ == "__main__":
  main()
