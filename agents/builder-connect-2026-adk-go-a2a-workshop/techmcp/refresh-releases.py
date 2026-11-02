#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Checks every SDK in technologies.json against GitHub and saves release data.

For each SDK it confirms that the repository (and, for monorepos, the path)
exists. For SDKs with their own repository it records the first and latest
GitHub release. The result goes to releases.json, which the server reads next
to technologies.json. Exits non-zero, without writing, if anything in
technologies.json is missing on GitHub.

Needs the gh CLI (logged in) or a GITHUB_TOKEN. Run it the day before the
workshop, then rebuild the server.
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

here = pathlib.Path(__file__).parent
techs = json.loads((here / "technologies.json").read_text())

repos = sorted({s["repo"] for t in techs["technologies"] for s in t["sdks"]})
paths = sorted({(s["repo"], s["path"]) for t in techs["technologies"] for s in t["sdks"] if s.get("path")})

fields = []
for i, repo in enumerate(repos):
    owner, name = repo.split("/")
    fields.append(
        f'r{i}: repository(owner: "{owner}", name: "{name}") {{ nameWithOwner isArchived stargazerCount '
        f'latestRelease {{ tagName publishedAt }} '
        f'releases(first: 1, orderBy: {{field: CREATED_AT, direction: ASC}}) {{ nodes {{ tagName publishedAt }} }} }}'
    )
for i, (repo, path) in enumerate(paths):
    owner, name = repo.split("/")
    fields.append(f'p{i}: repository(owner: "{owner}", name: "{name}") {{ object(expression: "HEAD:{path}") {{ __typename }} }}')
query = "query { " + " ".join(fields) + " }"


def graphql(q):
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req = urllib.request.Request(
            "https://api.github.com/graphql",
            data=json.dumps({"query": q}).encode(),
            headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
        )
        return json.load(urllib.request.urlopen(req))
    try:
        out = subprocess.run(["gh", "api", "graphql", "-f", f"query={q}"], capture_output=True, text=True)
    except FileNotFoundError:
        sys.exit("needs the gh CLI (logged in) or GITHUB_TOKEN")
    if not out.stdout:
        sys.exit(f"gh api graphql failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


data = graphql(query).get("data") or {}


def release(node):
    return {"tag": node["tagName"], "date": node["publishedAt"][:10]} if node else None


missing, result = [], {"generated": datetime.date.today().isoformat(), "repos": {}, "paths": {}}
for i, repo in enumerate(repos):
    r = data.get(f"r{i}")
    if not r:
        missing.append(repo)
        continue
    first = (r["releases"]["nodes"] or [None])[0]
    result["repos"][repo] = {
        "archived": r["isArchived"],
        "stars": r["stargazerCount"],
        "first_release": release(first),
        "latest_release": release(r["latestRelease"]),
    }
for i, (repo, path) in enumerate(paths):
    r = data.get(f"p{i}")
    if not r or not r["object"]:
        missing.append(f"{repo}/{path}")
        continue
    result["paths"][f"{repo}/{path}"] = True

if missing:
    sys.exit("not found on GitHub, fix technologies.json: " + ", ".join(missing))
(here / "releases.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(f"releases.json updated: {len(result['repos'])} repositories, {len(result['paths'])} paths")
