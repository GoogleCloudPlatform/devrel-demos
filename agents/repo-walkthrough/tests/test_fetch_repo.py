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

"""Unit and integration tests for skills/repo-walkthrough/scripts/fetch_repo.py."""

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import unittest.mock

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SKILL_SCRIPTS = REPO_ROOT / "skills" / "repo-walkthrough" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS if SKILL_SCRIPTS.is_dir() else REPO_ROOT / "scripts"))

import fetch_repo  # noqa: E402


class TestFetchRepo(unittest.TestCase):
  def test_normalize_repo_target(self):
    self.assertEqual(fetch_repo.normalize_repo_target("google/adk-python"), "google/adk-python")
    self.assertEqual(
        fetch_repo.normalize_repo_target("https://github.com/google/adk-python"),
        "google/adk-python",
    )
    self.assertEqual(
        fetch_repo.normalize_repo_target("https://github.com/google/adk-python.git"),
        "google/adk-python",
    )
    self.assertEqual(
        fetch_repo.normalize_repo_target("https://github.com/google/adk-python/tree/main/src"),
        "google/adk-python",
    )

  def test_validate_repo_slug_rejects_traversal(self):
    self.assertEqual(fetch_repo._validate_repo_slug("google/adk-python"), "google/adk-python")
    for invalid_slug in ("../etc", "owner/..", "owner/repo/extra", "", "-bad"):
      with self.assertRaises(ValueError):
        fetch_repo._validate_repo_slug(invalid_slug)

  def test_parse_github_target_and_scope_blobs(self):
    self.assertEqual(
        fetch_repo.parse_github_target("google/adk-python"),
        ("google/adk-python", None, ""),
    )
    self.assertEqual(
        fetch_repo.parse_github_target(
            "https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/data-analytics/cymbal-autos-multimodal"
        ),
        ("GoogleCloudPlatform/devrel-demos", "main", "data-analytics/cymbal-autos-multimodal"),
    )
    self.assertEqual(
        fetch_repo.parse_github_target(
            "https://github.com/owner/repo/blob/dev/packages/core/"
        ),
        ("owner/repo", "dev", "packages/core"),
    )

    tree_items = [
        {"type": "blob", "path": "README.md", "size": 500},
        {"type": "blob", "path": "other-demo/app.py", "size": 900},
        {"type": "blob", "path": "data-analytics/cymbal-autos-multimodal/scripts/03_vision.sql", "size": 1800},
        {"type": "blob", "path": "data-analytics/cymbal-autos-multimodal/app/src/app/page.tsx", "size": 4200},
        {"type": "tree", "path": "data-analytics/cymbal-autos-multimodal/app", "size": 0},
    ]
    scoped = fetch_repo._scope_blobs(tree_items, subpath="data-analytics/cymbal-autos-multimodal")
    self.assertEqual(
        scoped,
        [
            ("scripts/03_vision.sql", 1800),
            ("app/src/app/page.tsx", 4200),
        ],
    )

  def test_score_and_filter_paths(self):
    entries = [
        ("src/pkg/__init__.py", 1200),
        ("src/pkg/runner.py", 4800),
        ("src/pkg/agents/base_agent.py", 6500),
        ("scripts/setup/03_vision_extraction.sql", 1800),
        ("Dockerfile", 450),
        ("node_modules/pkg/index.js", 3000),
        ("tests/test_runner.py", 2200),
        ("dist/bundle.min.js", 90000),
        ("assets/logo.png", 14000),
    ]
    selected = fetch_repo.filter_and_rank_paths(entries, max_files=10)
    self.assertIn("src/pkg/__init__.py", selected)
    self.assertIn("src/pkg/runner.py", selected)
    self.assertIn("src/pkg/agents/base_agent.py", selected)
    self.assertIn("scripts/setup/03_vision_extraction.sql", selected)
    self.assertIn("Dockerfile", selected)
    self.assertNotIn("node_modules/pkg/index.js", selected)
    self.assertNotIn("tests/test_runner.py", selected)
    self.assertNotIn("dist/bundle.min.js", selected)
    self.assertNotIn("assets/logo.png", selected)

  def test_guess_layer(self):
    self.assertEqual(fetch_repo.guess_layer("src/pkg/__init__.py"), "entry")
    self.assertEqual(fetch_repo.guess_layer("src/pkg/cli/cli_tools.py"), "entry")
    self.assertEqual(fetch_repo.guess_layer("src/pkg/runners/runner.py"), "engine")
    self.assertEqual(fetch_repo.guess_layer("src/pkg/agents/llm_agent.py"), "agents")
    self.assertEqual(fetch_repo.guess_layer("src/pkg/flows/auto_flow.py"), "flows")
    self.assertEqual(fetch_repo.guess_layer("src/pkg/tools/base_tool.py"), "capabilities")

  def test_parse_file_metadata_python_js_sql_and_ipynb(self):
    py_src = '"""Core runner module."""\n\nclass Runner:\n  """Executes agent loops."""\n  pass\n\ndef run_once():\n  return True\n'
    py_meta = fetch_repo.parse_file_metadata("src/runner.py", py_src)
    self.assertEqual(py_meta["label"], "runner.py")
    self.assertEqual(py_meta["suggestedLayer"], "engine")
    self.assertEqual(py_meta["doc"], "Core runner module.")
    sym_names = [s["name"] for s in py_meta["symbols"]]
    self.assertIn("Runner", sym_names)
    self.assertIn("run_once()", sym_names)

    js_src = "// Main workflow orchestrator for walkthroughs\nexport async function buildWalkthrough() {\n  return 1;\n}\n"
    js_meta = fetch_repo.parse_file_metadata("scripts/build_walkthrough.mjs", js_src)
    self.assertEqual(js_meta["label"], "build_walkthrough.mjs")
    self.assertIn("buildWalkthrough", [s["name"] for s in js_meta["symbols"]])

    sql_src = "-- Extract multimodal vision features from GCS images\nCREATE OR REPLACE TABLE `model_dev.vision` AS\nSELECT * FROM `model_dev.meta`;\n"
    sql_meta = fetch_repo.parse_file_metadata("scripts/03_vision.sql", sql_src)
    self.assertEqual(sql_meta["doc"], "Extract multimodal vision features from GCS images")
    self.assertIn("CREATE OR REPLACE TABLE", sql_meta["snippetPreview"])

    nb_src = '{"cells":[{"cell_type":"markdown","source":["# Ignored prose"]},{"cell_type":"code","source":["def train_model():\\n","    return 42\\n"]}]}'
    nb_meta = fetch_repo.parse_file_metadata("notebooks/pipeline.ipynb", nb_src)
    self.assertIn("train_model()", [s["name"] for s in nb_meta["symbols"]])

  def test_fetch_local_dir_and_report(self):
    info = fetch_repo.fetch_local_dir(REPO_ROOT, max_files=15)
    self.assertEqual(info["repo"], REPO_ROOT.resolve().name)
    self.assertGreaterEqual(info["total_files"], 8)
    report = fetch_repo.build_analysis_report(info)
    paths = [c["path"] for c in report["candidates"]]
    self.assertIn("skills/repo-walkthrough/assets/index.tmpl", paths)
    self.assertIn("skills/repo-walkthrough/scripts/build_walkthrough.mjs", paths)
    self.assertNotIn("web/index.tmpl", paths)

  def test_symlink_containment_blocks_external_files(self):
    with tempfile.TemporaryDirectory() as outer_tmp:
      outer = pathlib.Path(outer_tmp)
      secret_file = outer / "outside_secret.py"
      secret_file.write_text("SECRET_TOKEN = 'do-not-read'\n", encoding="utf-8")
      repo_dir = outer / "repo"
      repo_dir.mkdir()
      (repo_dir / "main.py").write_text("def main():\n  return 1\n", encoding="utf-8")
      link_path = repo_dir / "escaped.py"
      try:
        os.symlink(secret_file, link_path)
      except OSError:
        # Windows without Developer Mode symlink privilege
        return
      info = fetch_repo.fetch_local_dir(repo_dir, max_files=10)
      self.assertIn("main.py", info["files"])
      self.assertNotIn("escaped.py", info["files"])

  def test_export_voice_markdown(self):
    with tempfile.TemporaryDirectory() as tmp:
      out_md = pathlib.Path(tmp) / "walkthrough.md"
      preset = {
          "title": "demo/repo",
          "subtitle": "Architecture Walkthrough",
          "walkthrough": [
              {"step": 1, "title": "Entry", "narration": "Starts at main.py.", "takeaway": "Entry point."}
          ],
      }
      fetch_repo.export_voice_markdown(preset, out_md)
      text = out_md.read_text(encoding="utf-8")
      self.assertIn("# demo/repo - Codebase Walkthrough", text)
      self.assertIn("## Step 1: Entry", text)
      self.assertIn("Starts at main.py.", text)

  def test_fetch_git_diff_rejects_flag_injection(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      tmp_repo = pathlib.Path(tmp)
      for bad_range in (
          "--output=/tmp/pwn",
          "-U99",
          "HEAD..--output=/tmp/pwn",
          "main...--exec=bad",
          "HEAD~1..HEAD\ninjected",
          "   ",
      ):
        with self.assertRaises(ValueError):
          fetch_repo.fetch_git_diff(tmp_repo, bad_range)

  def test_fetch_git_diff_utf8_non_ascii_ampersand_path_and_merge_base(self) -> None:
    raw_patch = (
        "diff --git a/app.py b/app.py\n"
        "index 111..222 100644\n"
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1,3 +1,4 @@\n"
        " def run():\n"
        "-    return 1\n"
        "+    return 2\n"
        "+    # updated\n"
    )
    preview = fetch_repo._extract_diff_preview(raw_patch)
    self.assertIn("@@ -1,3 +1,4 @@", preview)
    self.assertIn("-    return 1", preview)
    self.assertIn("+    return 2", preview)
    self.assertNotIn("diff --git", preview)

    if not shutil.which("git"):
      return

    with tempfile.TemporaryDirectory() as tmp:
      # Place repo inside a folder containing '&', spaces, and parentheses to test Windows/shell safety
      tmp_repo = pathlib.Path(tmp) / "R&D (Demo) Repo"
      (tmp_repo / "scripts").mkdir(parents=True)
      target = tmp_repo / "scripts" / "build_walkthrough.mjs"
      cafe_file = tmp_repo / "src" / "café.py"
      cafe_file.parent.mkdir(parents=True)

      subprocess.run(["git", "init", "-b", "main", str(tmp_repo)], check=True, capture_output=True)
      subprocess.run(["git", "-C", str(tmp_repo), "config", "user.email", "test@example.com"], check=True)
      subprocess.run(["git", "-C", str(tmp_repo), "config", "user.name", "Test"], check=True)

      target.write_text("export function run() {\n  return 1;\n}\n", encoding="utf-8")
      cafe_file.write_text('def menu():\n  return "café"\n', encoding="utf-8")
      subprocess.run(["git", "-C", str(tmp_repo), "add", "."], check=True)
      subprocess.run(["git", "-C", str(tmp_repo), "commit", "-m", "init"], check=True, capture_output=True)

      # Create feature branch modifying target + non-ASCII café.py
      subprocess.run(["git", "-C", str(tmp_repo), "checkout", "-b", "feat"], check=True, capture_output=True)
      target.write_text("export function run() {\n  return 2;\n  // updated\n}\n", encoding="utf-8")
      cafe_file.write_text('def menu():\n  return "crème brûlée"\n', encoding="utf-8")
      subprocess.run(["git", "-C", str(tmp_repo), "add", "."], check=True)
      subprocess.run(["git", "-C", str(tmp_repo), "commit", "-m", "feat: update café"], check=True, capture_output=True)

      # Advance main independently so 3-dot main...feat tests merge-base isolation
      subprocess.run(["git", "-C", str(tmp_repo), "checkout", "main"], check=True, capture_output=True)
      upstream_only = tmp_repo / "src" / "upstream_only.py"
      upstream_only.write_text("UPSTREAM = True\n", encoding="utf-8")
      subprocess.run(["git", "-C", str(tmp_repo), "add", "."], check=True)
      subprocess.run(["git", "-C", str(tmp_repo), "commit", "-m", "main: upstream commit"], check=True, capture_output=True)

      info = fetch_repo.fetch_git_diff(tmp_repo, "main...feat", max_files=12)
      report = fetch_repo.build_analysis_report(info)
      self.assertEqual(report["diffRange"], "main...feat")
      self.assertEqual(len(report["commits"]), 1)
      self.assertIn("feat: update café", report["commits"][0])
      by_path = {c["path"]: c for c in report["candidates"]}
      self.assertIn("scripts/build_walkthrough.mjs", by_path)
      self.assertIn("src/café.py", by_path)
      self.assertNotIn("src/upstream_only.py", by_path)
      self.assertEqual(by_path["src/café.py"]["diff"]["status"], "modified")

  def test_resolve_repo_root_and_open_target_cross_platform(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
      root = pathlib.Path(tmp)
      (root / "plugin.json").write_text('{"name":"repo-walkthrough"}', encoding="utf-8")
      skill_dir = root / "skills" / "repo-walkthrough"
      (skill_dir / "assets").mkdir(parents=True)
      (skill_dir / "assets" / "index.tmpl").write_text("<html>tmpl</html>", encoding="utf-8")
      deref_scripts = skill_dir / "scripts"
      deref_scripts.mkdir(parents=True)

      self.assertEqual(fetch_repo.resolve_repo_root(deref_scripts), root.resolve())
      # Without any built index.html, resolve_web_index must return None (never .tmpl)
      self.assertIsNone(fetch_repo.resolve_web_index(root.resolve()))

      # Standalone skill copy under .agents/skills/repo-walkthrough must resolve to the skill dir itself
      fake_agents = root / "project" / ".agents"
      standalone_skill = fake_agents / "skills" / "repo-walkthrough"
      (standalone_skill / "assets").mkdir(parents=True)
      (standalone_skill / "assets" / "index.tmpl").write_text("<html>tmpl</html>", encoding="utf-8")
      standalone_scripts = standalone_skill / "scripts"
      standalone_scripts.mkdir(parents=True)
      self.assertEqual(fetch_repo.resolve_repo_root(standalone_scripts), standalone_skill.resolve())

      # Built index.html is resolved cleanly
      (root / "web").mkdir(parents=True)
      (root / "web" / "index.html").write_text("<html>built</html>", encoding="utf-8")
      self.assertEqual(
          fetch_repo.resolve_web_index(root.resolve()),
          (root / "web" / "index.html").resolve(),
      )

    # Refuses .tmpl files on every platform
    self.assertFalse(fetch_repo.open_target(pathlib.Path("/tmp/index.tmpl"), platform="win32"))
    self.assertFalse(fetch_repo.open_target(pathlib.Path("/tmp/index.tmpl"), platform="darwin"))
    self.assertFalse(fetch_repo.open_target(pathlib.Path("/tmp/index.tmpl"), platform="linux"))

    # Windows uses os.startfile safely (no cmd /c start splitting on &, parens, or %TEMP%)
    opened_win: list[str] = []
    tricky_win_path = pathlib.Path(r"C:\Users\dev\R&D (1) %TEMP%\index.html")
    self.assertTrue(
        fetch_repo.open_target(
            tricky_win_path,
            platform="win32",
            startfile_fn=opened_win.append,
        )
    )
    self.assertEqual(opened_win, [str(tricky_win_path)])

    # Headless Linux missing xdg-open must not raise
    self.assertFalse(
        fetch_repo.open_target(
            pathlib.Path("/tmp/nonexistent.html"),
            platform="linux",
            runner=lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("xdg-open")),
        )
    )

  def test_sequence_and_mapping_inputs_accepted(self) -> None:
    entries = (("src/main.py", 600), ("src/runner.py", 1200))
    ranked = fetch_repo.filter_and_rank_paths(entries, max_files=5)
    self.assertEqual(set(ranked), {"src/main.py", "src/runner.py"})

    blobs = fetch_repo._scope_blobs(
        (types.MappingProxyType({"type": "blob", "path": "pkg/app.py", "size": 320}),),
        subpath="pkg",
    )
    self.assertEqual(blobs, [("app.py", 320)])

    with tempfile.TemporaryDirectory() as tmp:
      out_json = pathlib.Path(tmp) / "analysis.json"
      fetch_repo.main([str(REPO_ROOT), "--mode", "local", "--max-files", "4", "--json", str(out_json)])
      self.assertTrue(out_json.exists())

  def test_security_never_resolves_or_spawns_executables_from_untrusted_cwd(self) -> None:
    expected_script_dir = (REPO_ROOT / "skills" / "repo-walkthrough" / "scripts").resolve()

    # 1. Mocked win32 seam: even with a clean PATH, Windows shutil.which checks os.curdir unless
    # NoDefaultCurrentDirectoryInExePath=1 is set, and CreateProcessW searches cwd for bare names.
    with tempfile.TemporaryDirectory() as tmp:
      poison_cwd = pathlib.Path(tmp) / "untrusted-clone"
      poison_cwd.mkdir()
      for name in ("git.exe", "gh.exe", "rundll32.exe"):
        (poison_cwd / name).write_text("poison", encoding="utf-8")

      trusted_git_dir = r"C:\Program Files\Git\cmd"
      trusted_gh_dir = r"C:\Program Files\GitHub CLI"
      trusted_bins = {
          (trusted_git_dir.lower(), "git"): trusted_git_dir + r"\git.exe",
          (trusted_gh_dir.lower(), "gh"): trusted_gh_dir + r"\gh.exe",
      }

      def fake_win_which(cmd: str, mode: int = os.F_OK | os.X_OK, path: str | None = None) -> str | None:
        del mode
        if "\\" in cmd or "/" in cmd:
          parent, leaf = cmd.rsplit("\\", 1) if "\\" in cmd else cmd.rsplit("/", 1)
          stem = leaf[:-4].lower() if leaf.lower().endswith(".exe") else leaf.lower()
          return trusted_bins.get((parent.lower(), stem))
        raw_path = os.environ.get("PATH", "") if path is None else path
        search_dirs = raw_path.split(";") if raw_path else []
        if not os.environ.get("NoDefaultCurrentDirectoryInExePath"):
          search_dirs = [".", *search_dirs]
        stem = cmd[:-4].lower() if cmd.lower().endswith(".exe") else cmd.lower()
        for entry in search_dirs:
          cleaned = entry.strip().strip('"')
          if cleaned in ("", ".") or not (len(cleaned) >= 3 and cleaned[1] == ":"):
            candidate = poison_cwd / f"{stem}.exe"
            if candidate.exists():
              return f".\\{stem}.exe" if cleaned == "." else str(candidate)
            continue
          hit = trusted_bins.get((cleaned.lower(), stem))
          if hit:
            return hit
        return None

      recorded_spawns: list[tuple[list[str], dict[str, object]]] = []

      def fake_run(cmd: list[str], *args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        del args
        recorded_spawns.append((list(cmd), dict(kwargs)))
        stdout = ""
        if "log" in cmd:
          stdout = "abc1234 feat: demo\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

      def fake_check_output(cmd: list[str], *args: object, **kwargs: object) -> str:
        del args
        recorded_spawns.append((list(cmd), dict(kwargs)))
        if any(str(part).endswith("/git/trees/main?recursive=1") for part in cmd):
          return '{"tree": []}'
        return '{"default_branch": "main", "description": "demo", "stargazers_count": 1, "language": "Python"}'

      win_env = {
          "PATH": f";.;relative\\bin;{trusted_git_dir};{trusted_gh_dir}",
          "SystemRoot": r"C:\Windows",
      }
      orig_cwd = os.getcwd()
      os.chdir(poison_cwd)
      try:
        with (
            unittest.mock.patch.object(fetch_repo.sys, "platform", "win32"),
            unittest.mock.patch.dict(fetch_repo.os.environ, win_env, clear=True),
            unittest.mock.patch.object(fetch_repo.shutil, "which", side_effect=fake_win_which),
            unittest.mock.patch.object(fetch_repo.subprocess, "run", side_effect=fake_run),
            unittest.mock.patch.object(fetch_repo.subprocess, "check_output", side_effect=fake_check_output),
        ):
          self.assertTrue(fetch_repo.has_gh_cli())
          fetch_repo.fetch_github_via_gh("owner/repo", max_files=1)
          fetch_repo.fetch_git_diff(poison_cwd, "HEAD~1..HEAD", max_files=1)
          self.assertTrue(
              fetch_repo.open_target(
                  pathlib.Path(r"C:\out\index.html"),
                  platform="win32",
                  runner=fake_run,
              )
          )
      finally:
        os.chdir(orig_cwd)

      self.assertGreaterEqual(len(recorded_spawns), 6)
      for cmd, kwargs in recorded_spawns:
        exe = cmd[0]
        self.assertNotIn(str(poison_cwd).lower(), exe.lower(), f"resolved poison cwd binary: {exe}")
        self.assertFalse(exe.startswith("."), f"resolved relative cwd binary: {exe}")
        self.assertNotIn(exe.lower(), ("git", "git.exe", "gh", "gh.exe", "rundll32.exe"), f"unqualified exe: {exe}")
        self.assertEqual(pathlib.Path(str(kwargs.get("cwd"))).resolve(), expected_script_dir)
        child_env = kwargs.get("env")
        self.assertIsInstance(child_env, dict)
        assert isinstance(child_env, dict)
        self.assertEqual(child_env.get("NoDefaultCurrentDirectoryInExePath"), "1")

      rundll_cmd = recorded_spawns[-1][0][0]
      self.assertEqual(rundll_cmd, r"C:\Windows\System32\rundll32.exe")

      # When neither git nor gh is installed on trusted PATH dirs, poison <cwd>\git.exe and
      # <cwd>\gh.exe must never be resolved or spawned.
      trusted_bins.clear()
      recorded_spawns.clear()
      os.chdir(poison_cwd)
      try:
        with (
            unittest.mock.patch.object(fetch_repo.sys, "platform", "win32"),
            unittest.mock.patch.dict(fetch_repo.os.environ, win_env, clear=True),
            unittest.mock.patch.object(fetch_repo.shutil, "which", side_effect=fake_win_which),
            unittest.mock.patch.object(fetch_repo.subprocess, "run", side_effect=fake_run),
            unittest.mock.patch.object(fetch_repo.subprocess, "check_output", side_effect=fake_check_output),
        ):
          self.assertFalse(fetch_repo.has_gh_cli(), "must not resolve poison <cwd>\\gh.exe")
          with self.assertRaises(FileNotFoundError):
            fetch_repo.fetch_github_via_gh("owner/repo", max_files=1)
          with self.assertRaises(RuntimeError):
            fetch_repo.fetch_git_diff(poison_cwd, "HEAD~1..HEAD", max_files=1)
      finally:
        os.chdir(orig_cwd)
      self.assertEqual(recorded_spawns, [], "must never spawn when only poison cwd binaries exist")

    # 2. Real subprocess check with a poisoned cwd and '.' / empty entries in PATH.
    real_git = shutil.which("git")
    if not real_git:
      return
    with tempfile.TemporaryDirectory() as tmp:
      poison_repo = pathlib.Path(tmp) / "hostile-repo"
      poison_repo.mkdir()
      marker = pathlib.Path(tmp) / "PWNED"
      real_git_dir = str(pathlib.Path(real_git).resolve().parent)

      subprocess.run([real_git, "init", "-b", "main", str(poison_repo)], check=True, capture_output=True)
      subprocess.run([real_git, "-C", str(poison_repo), "config", "user.email", "t@example.com"], check=True)
      subprocess.run([real_git, "-C", str(poison_repo), "config", "user.name", "T"], check=True)
      (poison_repo / "app.py").write_text("x = 1\n", encoding="utf-8")
      subprocess.run([real_git, "-C", str(poison_repo), "add", "app.py"], check=True)
      subprocess.run([real_git, "-C", str(poison_repo), "commit", "-m", "c1"], check=True, capture_output=True)
      (poison_repo / "app.py").write_text("x = 2\n", encoding="utf-8")
      subprocess.run([real_git, "-C", str(poison_repo), "add", "app.py"], check=True)
      subprocess.run([real_git, "-C", str(poison_repo), "commit", "-m", "c2"], check=True, capture_output=True)

      # Isolated trusted bin dir containing ONLY a symlink to real git (no gh), so any gh hit is poison.
      trusted_dir = pathlib.Path(tmp) / "trusted-bin"
      trusted_dir.mkdir()
      try:
        os.symlink(real_git, trusted_dir / "git")
      except OSError:
        trusted_dir = pathlib.Path(real_git_dir)

      for tool in ("git", "gh"):
        script = poison_repo / tool
        script.write_text(
            f"#!/bin/sh\nprintf '%s\\n' '{tool}' >> '{marker}'\nexit 0\n",
            encoding="utf-8",
        )
        script.chmod(0o755)

      hostile_path = f":.:relative/bin:{trusted_dir}"
      orig_cwd = os.getcwd()
      os.chdir(poison_repo)
      try:
        with unittest.mock.patch.dict(os.environ, {"PATH": hostile_path}, clear=False):
          if trusted_dir != pathlib.Path(real_git_dir):
            self.assertFalse(fetch_repo.has_gh_cli(), "keyless/gh-less host must not execute ./gh in cwd")
          diff_info = fetch_repo.fetch_git_diff(poison_repo, "HEAD~1..HEAD", max_files=4)
          self.assertIn("app.py", diff_info["files"])
      finally:
        os.chdir(orig_cwd)

      self.assertFalse(marker.exists(), f"poison binary in cwd was executed: {marker.read_text() if marker.exists() else ''}")


if __name__ == "__main__":
  unittest.main()
