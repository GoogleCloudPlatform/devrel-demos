import sqlite3
import json
import collections
import re
import sys
import argparse
import os

# Import Success Determinants logic
# Assuming success_determinants.py is in the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from success_determinants import analyze_success_determinants

# Default Configuration
DEFAULT_DB_PATH = "agents/tenkai/experiments/tenkai.db"

def get_db_path():
    return os.environ.get("TENKAI_DB_PATH", DEFAULT_DB_PATH)

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

def analyze_experiment(exp_id):
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Experiment Details
    cursor.execute("SELECT name, config_content FROM experiments WHERE id = ?", (exp_id,))
    row = cursor.fetchone()
    if not row:
        print(f"Experiment {exp_id} not found.")
        return
    exp_name, config_content = row
    
    print(f"# Analysis: {exp_name} (ID: {exp_id})\n")
    
    # 2. High-Level Stats
    print("## 1. Performance Overview\n")
    print("| Alternative | Success Rate | Avg Duration (s) | Avg Tokens |")
    print("|---|---|---|---|")
    
    cursor.execute("""
        SELECT 
            alternative, 
            COUNT(*) as total, 
            SUM(is_success) as successes, 
            AVG(duration)/1e9 as avg_dur, 
            AVG(total_tokens) as avg_tok 
        FROM run_results 
        WHERE experiment_id = ? 
        GROUP BY alternative
        ORDER BY avg_dur ASC
    """, (exp_id,))
    
    alternatives = []
    for row in cursor.fetchall():
        alt, total, success, dur, tok = row
        success_rate = (success / total) * 100 if total > 0 else 0
        print(f"| **{alt}** | {success}/{total} ({success_rate:.1f}%) | {dur:.1f} | {tok:.0f} |")
        alternatives.append(alt)
    print("")

    # 3. Tool Usage Analysis
    print("## 2. Tool Usage Breakdown\n")
    
    # Define specialized tools (heuristically, anything not shell/basic file ops)
    # Actually, let's just count them and let the user decide.
    # But for "Shell vs Specialized", we need lists.
    SHELL_TOOLS = {'run_shell_command'}
    BASIC_TOOLS = {'write_file', 'read_file', 'replace', 'list_directory', 'google_web_search'}
    
    # Get tool usage from run_events to get granular details
    tool_counts = collections.defaultdict(lambda: collections.Counter())
    shell_categories = collections.defaultdict(collections.Counter)
    
    cursor.execute("""
        SELECT 
            r.alternative,
            re.payload
        FROM run_results r
        JOIN run_events re ON r.id = re.run_id
        WHERE r.experiment_id = ? AND re.type = 'tool'
    """, (exp_id,))
    
    for alt, payload_json in cursor.fetchall():
        try:
            payload = json.loads(payload_json)
            name = payload.get('name')
            tool_counts[alt][name] += 1
            
            if name == 'run_shell_command':
                args = payload.get('args', {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except:
                        args = {}
                cmd = args.get('command', '')
                cat = classify_shell_command(cmd)
                shell_categories[alt][cat] += 1
                
        except json.JSONDecodeError:
            continue
            
    print("| Alternative | Shell Calls | Specialized Calls |")
    print("|---|---|---|")
    
    for alt in alternatives:
        counts = tool_counts[alt]
        total = sum(counts.values())
        if total == 0:
            print(f"| {alt} | 0 | 0 |")
            continue
            
        shell_c = counts['run_shell_command']
        special_c = total - shell_c
        
        print(f"| {alt} | {shell_c} ({(shell_c/total)*100:.0f}%) | {special_c} ({(special_c/total)*100:.0f}%) |")
    print("")

    # 4. Failure Analysis
    print("## 3. Failure Analysis\n")
    
    failures = collections.defaultdict(list)
    
    # We look for explicit error events OR tool events with non-zero exit codes/error outputs
    # Let's re-use the logic from previous scripts but more streamlined.
    
    # A. Check failed runs in run_results for the "reason" column if populated, or errors
    # Actually, let's scan the tool events for errors as that was most useful.
    
    # Re-scan events for errors
    cursor.execute("""
        SELECT 
            r.alternative,
            re.type,
            re.payload
        FROM run_results r
        JOIN run_events re ON r.id = re.run_id
        WHERE r.experiment_id = ? AND (re.type = 'tool' OR re.type = 'error')
    """, (exp_id,))
    
    for alt, etype, payload_json in cursor.fetchall():
        try:
            payload = json.loads(payload_json)
            
            if etype == 'error':
                msg = payload.get('message', 'Unknown Error')
                failures[alt].append(f"[System] {msg}")
                continue
            
            # Tool analysis
            name = payload.get('name')
            output = payload.get('output', '')
            
            if name == 'run_shell_command':
                if "Exit Code:" in output:
                     match = re.search(r'Exit Code: (\d+)', output)
                     if match and int(match.group(1)) != 0:
                         # Try to classify the command
                         args = payload.get('args', {})
                         if isinstance(args, str):
                             try: args = json.loads(args)
                             except: args = {}
                         cmd = args.get('command', '')
                         cat = classify_shell_command(cmd)
                         failures[alt].append(f"Shell: {cat} (Exit {match.group(1)})")
                
                # Heuristics for shell failures without exit code or specific errors
                if "command not found" in output:
                    failures[alt].append(f"Shell: Command Not Found")
            
            # Generic tool errors
            if payload.get('error'):
                failures[alt].append(f"Tool: {name} ({payload.get('error')[:50]}...)")
            elif output.startswith("Error:"):
                failures[alt].append(f"Tool: {name} ({output[:50]}...)")
                
        except:
            continue

    for alt in alternatives:
        fails = failures[alt]
        if not fails:
            continue
            
        print(f"### {alt} Failures")
        c = collections.Counter(fails)
        for err, count in c.most_common(5):
            print(f"- {err}: {count}")
        print("")

    conn.close()
    
    # 5. Success Determinants (Imported)
    analyze_success_determinants(exp_id)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_experiment.py <EXP_ID>")
        sys.exit(1)
    
    analyze_experiment(sys.argv[1])
