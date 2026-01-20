import sqlite3
import json

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63
ALT_V2 = "godoctor-advanced-safe-shell-v2"

def dump_go_mod_failures():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, t.payload 
        FROM run_results r
        JOIN run_events t ON r.id = t.run_id
        WHERE r.experiment_id = ? AND r.alternative = ? AND t.type = 'tool'
        ORDER BY r.id, t.id
    """, (EXP_ID, ALT_V2))
    
    events = cursor.fetchall()
    
    count = 0
    print(f"{ 'Run ID':<8} | {'Command':<25} | {'Args':<40} | {'Error/Output'}")
    print("-" * 120)

    for run_id, payload_json in events:
        try:
            payload = json.loads(payload_json)
            tool_name = payload.get('name')
            
            if tool_name != 'go_mod':
                continue

            status = payload.get('status')
            output = payload.get('output', '')
            
            # Parse Args
            args_str = payload.get('args')
            try:
                if isinstance(args_str, str):
                    tool_args = json.loads(args_str)
                else:
                    tool_args = args_str or {}
            except:
                tool_args = {}
                
            subcmd = tool_args.get('command', 'tidy')
            mod_args = tool_args.get('args', [])
            
            # Filter for failures
            if status == 'error' or 'failed' in output.lower() or 'error' in output.lower():
                count += 1
                # Truncate output
                display_out = output.replace("\n", " ")[:60] + "..."
                print(f"{run_id:<8} | {subcmd:<25} | {str(mod_args):<40} | {display_out}")

        except Exception as e:
            continue

    if count == 0:
        print("No go_mod failures found.")

    conn.close()

if __name__ == "__main__":
    dump_go_mod_failures()
