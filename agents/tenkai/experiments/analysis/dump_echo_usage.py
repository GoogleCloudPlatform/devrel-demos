import sqlite3
import json

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63
ALT_V2 = "godoctor-advanced-safe-shell-v2"

def dump_echo_usage():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get V2 Run IDs
    cursor.execute("SELECT id FROM run_results WHERE experiment_id = ? AND alternative = ?", (EXP_ID, ALT_V2))
    run_ids = [row[0] for row in cursor.fetchall()]

    print(f"Scanning {len(run_ids)} V2 runs for 'echo' usage...")
    print("-" * 80)

    count = 0
    for run_id in run_ids:
        cursor.execute("SELECT payload FROM run_events WHERE run_id = ? AND type = 'tool'", (run_id,))
        rows = cursor.fetchall()
        
        for (payload_json,) in rows:
            try:
                payload = json.loads(payload_json)
                tool_name = payload.get('name')
                
                if tool_name != 'safe_shell':
                    continue

                args_str = payload.get('args')
                if isinstance(args_str, str):
                    args = json.loads(args_str)
                else:
                    args = args_str or {}
                
                cmd = args.get('command', '')
                arg_list = args.get('args', [])
                
                # Check for explicit 'echo' command OR 'echo' inside sh -c arguments
                is_echo = cmd == 'echo'
                is_embedded_echo = False
                
                if not is_echo and (cmd.endswith('sh') or cmd == 'bash'):
                    # Check if echo is in the script string
                    for a in arg_list:
                        if 'echo' in a:
                            is_embedded_echo = True
                            break
                
                if is_echo or is_embedded_echo:
                    count += 1
                    print(f"[Run {run_id}]")
                    print(f"  Type: {'Direct Command' if is_echo else 'Subshell Script'}")
                    print(f"  Raw Args: {json.dumps(args, indent=2)}")
                    print(f"  Output: {payload.get('output', '')[:200]}...") # Truncate output
                    print("-" * 40)

            except Exception as e:
                print(f"Error parsing event: {e}")
                continue

    if count == 0:
        print("No 'echo' usage found.")

    conn.close()

if __name__ == "__main__":
    dump_echo_usage()
