import sqlite3
import json
from collections import Counter, defaultdict

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63
ALT_V2 = "godoctor-advanced-safe-shell-v2"

def analyze_v2_shell_usage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT t.payload 
        FROM run_results r
        JOIN run_events t ON r.id = t.run_id
        WHERE r.experiment_id = ? AND r.alternative = ? AND t.type = 'tool'
        ORDER BY t.id
    """, (EXP_ID, ALT_V2))
    
    events = cursor.fetchall()
    
    cmd_stats = Counter()
    cmd_outcomes = defaultdict(lambda: {"success": 0, "error": 0, "blocked": 0})
    
    for (payload_json,) in events:
        try:
            payload = json.loads(payload_json)
        except:
            continue
            
        tool_name = payload.get('name')
        if tool_name != 'safe_shell':
            continue
            
        args_str = payload.get('args')
        try:
            if isinstance(args_str, str):
                tool_args = json.loads(args_str)
            else:
                tool_args = args_str or {}
        except:
            continue
            
        # Reconstruct command string
        base_cmd = tool_args.get('command', '')
        args_list = tool_args.get('args', [])
        full_cmd = f"{base_cmd} {' '.join(args_list)}".strip()
        
        cmd_stats[full_cmd] += 1
        
        status = payload.get('status')
        output = payload.get('output', '')
        
        if "Blocked" in output or "Permission Denied" in output:
            cmd_outcomes[full_cmd]["blocked"] += 1
        elif status == 'error' or 'Error' in output: # Broad error check
             cmd_outcomes[full_cmd]["error"] += 1
        else:
             cmd_outcomes[full_cmd]["success"] += 1

    print(f"{'Command':<60} | {'Count':<6} | {'Success':<8} | {'Error':<6} | {'Blocked'}")
    print("-" * 100)
    
    for cmd, count in cmd_stats.most_common(20):
        out = cmd_outcomes[cmd]
        # Truncate cmd for display
        display_cmd = (cmd[:57] + '...') if len(cmd) > 57 else cmd
        print(f"{display_cmd:<60} | {count:<6} | {out['success']:<8} | {out['error']:<6} | {out['blocked']}")

    conn.close()

if __name__ == "__main__":
    analyze_v2_shell_usage()
