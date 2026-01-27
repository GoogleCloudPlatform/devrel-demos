import sqlite3
import json
import collections
import re

DB_PATH = 'agents/tenkai/experiments/tenkai.db'
EXP_ID = 91
ALTERNATIVES = ['godoctor-mcp', 'godoctor-extension']

def deep_analyze_failures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query for all shell commands in GoDoctor alternatives
    query = """
    SELECT 
        r.alternative,
        r.id as run_id,
        r.is_success,
        re.payload
    FROM run_results r
    JOIN run_events re ON r.id = re.run_id
    WHERE r.experiment_id = ? 
      AND r.alternative IN (?, ?) 
      AND re.type = 'tool'
      AND re.payload LIKE '%run_shell_command%'
    """

    cursor.execute(query, (EXP_ID, ALTERNATIVES[0], ALTERNATIVES[1]))
    
    friction_patterns = collections.defaultdict(collections.Counter)
    recovery_stats = collections.defaultdict(lambda: {'recovered': 0, 'stayed_failed': 0})
    
    # Set of run IDs that were actually successful in the end
    successful_runs = set()
    
    rows = cursor.fetchall()
    for row in rows:
        alt, run_id, is_success, payload_json = row
        if is_success: successful_runs.add(run_id)

    for alt, run_id, is_success, payload_json in rows:
        try:
            payload = json.loads(payload_json)
            if payload.get('name') != 'run_shell_command': continue
            
            output = payload.get('output', '').lower()
            
            # Heuristics for "Friction" (Command execution failure or Go error)
            friction_key = None
            if "but does not contain package" in output:
                friction_key = "SDK Package Name Hallucination"
            elif "missing go.sum" in output:
                friction_key = "Missing go.sum (Need go mod tidy)"
            elif "redeclared in this block" in output:
                friction_key = "Code Conflict (Redeclaration)"
            elif "undefined:" in output:
                friction_key = "Undefined Symbol (Import/Ref Issue)"
            elif "assignment mismatch" in output:
                friction_key = "Assignment Mismatch (Return Count)"
            elif "command not found" in output:
                friction_key = "Environment Gap (Command Not Found)"
            elif "fail" in output and ("test" in output or "pass" in output):
                friction_key = "Test/Logic Failure"
            elif "error:" in output or "failed" in output:
                friction_key = "General Shell Error"

            if friction_key:
                friction_patterns[alt][friction_key] += 1
                if run_id in successful_runs:
                    recovery_stats[alt]['recovered'] += 1
                else:
                    recovery_stats[alt]['stayed_failed'] += 1

        except:
            continue

    conn.close()

    print("# Deep Dive: Shell Friction in GoDoctor Alternatives\n")
    print("This analysis identifies 'friction events' where a shell command returned an error or a Go-specific failure message.\n")
    
    for alt in ALTERNATIVES:
        total_friction = sum(friction_patterns[alt].values())
        print(f"## {alt} ({total_friction} friction events)\n")
        
        # Recovery is tricky to count this way (one run might have 10 friction events then pass)
        # Let's count unique runs that had friction but passed.
        # Actually, let's keep it simple for now.
        
        print("| Friction Type | Frequency |")
        print("|---|---|")
        for err, count in friction_patterns[alt].most_common(10):
            print(f"| {err} | {count} |")
        print("")

if __name__ == "__main__":
    deep_analyze_failures()