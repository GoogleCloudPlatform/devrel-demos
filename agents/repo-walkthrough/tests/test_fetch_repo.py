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

      # Standalone skill copy under ~/.gemini/skills/repo-walkthrough must resolve to the skill dir itself
      fake_gemini = root / "home" / ".gemini"
      standalone_skill = fake_gemini / "skills" / "repo-walkthrough"
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


if __name__ == "__main__":
  unittest.main()
