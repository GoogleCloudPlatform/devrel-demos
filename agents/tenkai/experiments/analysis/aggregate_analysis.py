import sqlite3
import json
from collections import defaultdict

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63
ALT_V1 = "godoctor-advanced-no-core"
ALT_V2 = "godoctor-advanced-safe-shell-v2"

def analyze_runs(cursor, alt):
    cursor.execute("""
        SELECT r.id, r.is_success, t.payload
        FROM run_results r
        JOIN run_events t ON r.id = t.run_id
        WHERE r.experiment_id = ? AND r.alternative = ? AND (t.type = 'tool' OR t.type = 'result')
        ORDER BY r.id, t.id
    """, (EXP_ID, alt))
    
    rows = cursor.fetchall()
    
    run_data = defaultdict(lambda: {
        'success': False, 
        'build_attempts': [], 
        'shell_blocks': 0, 
        'silent_blocks': 0,
        'build_failures': 0
    })
    
    pending_tool = None
    
    for run_id, is_success, payload_json in rows:
        run_data[run_id]['success'] = is_success
        try:
            payload = json.loads(payload_json)
        except:
            continue
            
        if 'name' in payload: # Tool Call (simplified logic)
            pending_tool = payload
        elif 'status' in payload: # Tool Result
            if not pending_tool: continue
            
            tool_name = pending_tool.get('name')
            tool_args_str = pending_tool.get('args')
            try:
                if isinstance(tool_args_str, str):
                    tool_args = json.loads(tool_args_str)
                else:
                    tool_args = tool_args_str
            except:
                tool_args = {}

            output = payload.get('output', '')
            status = payload.get('status', '')
            
            # Analyze go_build
            if tool_name == 'go_build':
                pkgs = tool_args.get('packages', [])
                if status == 'error' or 'Build Failed' in output:
                    run_data[run_id]['build_failures'] += 1
                    run_data[run_id]['build_attempts'].append(f"FAIL: {pkgs}")
                else:
                    run_data[run_id]['build_attempts'].append(f"OK: {pkgs}")

            # Analyze safe_shell
            if tool_name == 'safe_shell':
                if "Blocked:" in output:
                    run_data[run_id]['shell_blocks'] += 1
                    # Check for Silent Block (Success status but Blocked message)
                    if status == 'success':
                        run_data[run_id]['silent_blocks'] += 1

            pending_tool = None

    print(f"\n=== Analysis for {alt} ===")
    print(f"Total Runs: {len(run_data)}")
    
    # Aggregates
    total_build_fails = sum(d['build_failures'] for d in run_data.values())
    total_silent_blocks = sum(d['silent_blocks'] for d in run_data.values())
    
    print(f"Total Build Failures: {total_build_fails}")
    print(f"Total Silent Blocks (V2 Bug): {total_silent_blocks}")
    
    # Pattern Matching
    root_builds = 0
    subdir_builds = 0
    
    for rid, data in run_data.items():
        for attempt in data['build_attempts']:
            if "FAIL: ['.']" in attempt or "FAIL: ['.', '-o']" in attempt: # Rough check
                # Check args more carefully in a real parser, but string match works for summary
                pass
            
            # Heuristic: if packages contains "/" it's likely a subdir
            if any("/" in str(x) for x in attempt): 
                subdir_builds += 1
            else:
                root_builds += 1

    print(f"Root Build Attempts (approx): {root_builds}")
    print(f"Subdir Build Attempts (approx): {subdir_builds}")

    # Correlation Check
    fails_with_silent_blocks = sum(1 for d in run_data.values() if not d['success'] and d['silent_blocks'] > 0)
    success_with_silent_blocks = sum(1 for d in run_data.values() if d['success'] and d['silent_blocks'] > 0)
    
    print(f"Failed Runs involving Silent Blocks: {fails_with_silent_blocks}")
    print(f"Successful Runs involving Silent Blocks: {success_with_silent_blocks}")

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    analyze_runs(cursor, ALT_V1)
    analyze_runs(cursor, ALT_V2)
    conn.close()

if __name__ == "__main__":
    main()
