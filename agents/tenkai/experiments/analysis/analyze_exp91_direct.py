import sqlite3
import json
import collections
import re

DB_PATH = 'agents/tenkai/experiments/tenkai.db'
EXP_ID = 91

def classify_shell_command(cmd):
    cmd = cmd.strip()
    if cmd.startswith("go mod init"): return "go mod init"
    if cmd.startswith("go mod tidy"): return "go mod tidy"
    if cmd.startswith("go get"): return "go get"
    if cmd.startswith("go build"): return "go build"
    if cmd.startswith("go test"): return "go test"
    if cmd.startswith("go list"): return "go list"
    if cmd.startswith("go doc"): return "go doc"
    if cmd.startswith("go vet"): return "go vet"
    if cmd.startswith("go fmt") or cmd.startswith("gofmt"): return "go fmt"
    if cmd.startswith("mkdir"): return "mkdir"
    if cmd.startswith("ls"): return "ls/dir"
    if cmd.startswith("cat") or cmd.startswith("read_file"): return "cat/read"
    if cmd.startswith("grep"): return "grep"
    if cmd.startswith("rm"): return "rm"
    if "golangci-lint" in cmd: return "golangci-lint"
    if "staticcheck" in cmd: return "staticcheck"
    return "other"

failures = collections.defaultdict(list)
shell_commands = collections.defaultdict(collections.Counter)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

query = """
SELECT 
    r.alternative,
    re.payload
FROM run_results r
JOIN run_events re ON r.id = re.run_id
WHERE r.experiment_id = ? AND re.type = 'tool'
"""

cursor.execute(query, (EXP_ID,))

for alternative, payload_json in cursor.fetchall():
    try:
        payload = json.loads(payload_json)
        tool_name = payload.get('name')
        tool_args = payload.get('args', {})
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except:
                tool_args = {}
        
        tool_output = payload.get('output', '')
        
        # Analyze run_shell_command
        if tool_name == 'run_shell_command':
            cmd = tool_args.get('command', '')
            category = classify_shell_command(cmd)
            shell_commands[alternative][category] += 1
            
            # Check for failure in output text
            if "Exit Code:" in tool_output:
                # Extract exit code
                match = re.search(r'Exit Code: (\d+)', tool_output)
                if match:
                    exit_code = int(match.group(1))
                    if exit_code != 0:
                        # Extract error message (stderr or output)
                        # The tool output format puts Output: ... and Error: ... 
                        # We'll take a snippet of the output as the error reason
                        error_snippet = tool_output[:200].replace('\n', ' ')
                        failures[alternative].append((tool_name, f"{category} (Exit {exit_code})"))

        # Analyze other tools
        else:
            # Check for explicit error field or "Error:" prefix in output
            if payload.get('error'):
                 failures[alternative].append((tool_name, payload.get('error')))
            elif tool_output.startswith("Error:"):
                 failures[alternative].append((tool_name, tool_output[:100]))

    except json.JSONDecodeError:
        continue

conn.close()

print("# Analysis of Experiment 91 Failures & Patterns\n")

print("## 1. Tool Call Failures by Alternative\n")
for alt, fails in failures.items():
    print(f"### {alt} ({len(fails)} failures)")
    c = collections.Counter(fails)
    for (tool, err), count in c.most_common(10):
        print(f"- **{tool}**: `{err}` ({count}x)")
    print("")

print("## 2. Shell Command Usage Patterns\n")
print("| Command Category | Default | Extension | MCP | Total |")
print("|---|---|---|---|---|")

all_categories = set()
for c in shell_commands.values():
    all_categories.update(c.keys())

# Sort categories by total usage
cat_totals = {}
for cat in all_categories:
    cat_totals[cat] = sum(shell_commands[alt][cat] for alt in shell_commands)

for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
    def_count = shell_commands['default'][cat]
    ext_count = shell_commands['godoctor-extension'][cat]
    mcp_count = shell_commands['godoctor-mcp'][cat]
    print(f"| {cat} | {def_count} | {ext_count} | {mcp_count} | {total} |")
