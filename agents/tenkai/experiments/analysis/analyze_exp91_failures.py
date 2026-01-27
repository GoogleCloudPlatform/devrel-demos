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
shell_failures = collections.defaultdict(collections.Counter)

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
        
        # Handle args being string or dict
        tool_args = payload.get('args', {})
        if isinstance(tool_args, str):
            try:
                tool_args = json.loads(tool_args)
            except:
                tool_args = {}
        
        tool_output = payload.get('output', '')
        
        is_failure = False
        failure_reason = ""

        # Analyze run_shell_command
        if tool_name == 'run_shell_command':
            cmd = tool_args.get('command', '')
            category = classify_shell_command(cmd)
            shell_commands[alternative][category] += 1
            
            # Check for failure signals
            if "Exit Code:" in tool_output:
                match = re.search(r'Exit Code: (\d+)', tool_output)
                if match:
                    exit_code = int(match.group(1))
                    if exit_code != 0:
                        is_failure = True
                        failure_reason = f"{category} (Exit {exit_code})"

            # Heuristics for failures in output text if exit code is 0 (or not found)
            if not is_failure:
                if category == "go test" and ("FAIL" in tool_output or "build failed" in tool_output):
                     is_failure = True
                     failure_reason = f"{category} (Test Failed)"
                elif "command not found" in tool_output:
                     is_failure = True
                     failure_reason = f"{category} (Command Not Found)"
            
            if is_failure:
                shell_failures[alternative][category] += 1
                failures[alternative].append((tool_name, failure_reason))

        # Analyze other tools
        else:
            if payload.get('error'):
                 is_failure = True
                 failure_reason = payload.get('error')
            elif tool_output.startswith("Error:"):
                 is_failure = True
                 failure_reason = tool_output[:100].replace('\n', ' ')
            
            if is_failure:
                failures[alternative].append((tool_name, failure_reason))

    except json.JSONDecodeError:
        continue

conn.close()

print("# Analysis of Experiment 91 Failures & Patterns\n")

print("## 1. Tool Call Failures by Alternative\n")
for alt, fails in failures.items():
    print(f"### {alt} ({len(fails)} detected failures)")
    c = collections.Counter(fails)
    for (tool, err), count in c.most_common(10):
        print(f"- **{tool}**: `{err}` ({count}x)")
    print("")

print("## 2. Shell Command Usage & Failure Rates\n")
print("| Command Category | Default (Use/Fail) | Extension (Use/Fail) | MCP (Use/Fail) | Total Uses |")
print("|---|---|---|---|---|")

all_categories = set()
for c in shell_commands.values():
    all_categories.update(c.keys())

# Sort categories by total usage
cat_totals = {}
for cat in all_categories:
    cat_totals[cat] = sum(shell_commands[alt][cat] for alt in shell_commands)

for cat, total in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
    def_use = shell_commands['default'][cat]
    def_fail = shell_failures['default'][cat]
    
    ext_use = shell_commands['godoctor-extension'][cat]
    ext_fail = shell_failures['godoctor-extension'][cat]
    
    mcp_use = shell_commands['godoctor-mcp'][cat]
    mcp_fail = shell_failures['godoctor-mcp'][cat]
    
    print(f"| {cat} | {def_use} / {def_fail} | {ext_use} / {ext_fail} | {mcp_use} / {mcp_fail} | {total} |")