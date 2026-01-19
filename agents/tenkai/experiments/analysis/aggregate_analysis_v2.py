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
        WHERE r.experiment_id = ? AND r.alternative = ? AND t.type = 'tool'
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
    
    for run_id, is_success, payload_json in rows:
        run_data[run_id]['success'] = is_success
        try:
            payload = json.loads(payload_json)
        except:
            continue
            
        tool_name = payload.get('name')
        status = payload.get('status')
        output = payload.get('output', '')
        
        # Parse Args
        tool_args_str = payload.get('args')
        try:
            if isinstance(tool_args_str, str):
                tool_args = json.loads(tool_args_str)
            else:
                tool_args = tool_args_str or {}
        except:
            tool_args = {}

        # Analyze go_build
        if tool_name == 'go_build':
            pkgs = tool_args.get('packages', [])
            args = tool_args.get('args', []) # sometimes args are here
            
            # Combine for signature
            sig = f"pkgs={pkgs} args={args}"
            
            if status == 'error' or 'Build Failed' in output:
                run_data[run_id]['build_failures'] += 1
                run_data[run_id]['build_attempts'].append(f"FAIL: {sig}")
            else:
                run_data[run_id]['build_attempts'].append(f"OK: {sig}")

        # Analyze safe_shell
        if tool_name == 'safe_shell':
            if "Blocked" in output or "Permission Denied" in output:
                run_data[run_id]['shell_blocks'] += 1
                # Check for Silent Block (Success status but Blocked message)
                if status == 'success':
                    run_data[run_id]['silent_blocks'] += 1

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
        if not data['build_attempts']: continue
        
        # Heuristic: look at the FIRST build attempt to see strategy
        first_attempt = data['build_attempts'][0]
        
        if "pkgs=['.']" in first_attempt or 'pkgs=["."]' in first_attempt:
            root_builds += 1
        elif "pkgs=['./...']" in first_attempt: # Recursive root
            root_builds += 1
        elif "pkgs=['./cmd" in first_attempt or 'pkgs=["./cmd"' in first_attempt:
            subdir_builds += 1
        else:
            # Fallback for weird args
            pass

    print(f"Initial Strategy - Root Build: {root_builds}")
    print(f"Initial Strategy - Subdir Build: {subdir_builds}")

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