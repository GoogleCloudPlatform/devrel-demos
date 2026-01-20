import sqlite3
import json

db_path = "agents/tenkai/experiments/tenkai.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get godoctor runs
cursor.execute("SELECT id FROM run_results WHERE experiment_id = 72 AND alternative = 'godoctor'")
run_ids = [row[0] for row in cursor.fetchall()]

print(f"Analyzing {len(run_ids)} runs for 'godoctor' alternative...")

for run_id in run_ids:
    cursor.execute("SELECT type, payload FROM run_events WHERE run_id = ? ORDER BY id", (run_id,))
    events = cursor.fetchall()
    
    used_godoctor = False
    used_shell = False
    godoctor_tools = []
    
    for evt_type, content in events:
        if evt_type == "tool_use":
            try:
                data = json.loads(content)
                tool_name = data.get("tool_name")
                if tool_name:
                    if tool_name == "run_shell_command":
                        used_shell = True
                    elif tool_name.startswith("go_") or tool_name.startswith("file_") or tool_name == "safe_shell":
                        used_godoctor = True
                        if tool_name not in godoctor_tools:
                            godoctor_tools.append(tool_name)
            except:
                pass

    if used_godoctor:
        print(f"Run {run_id}: USED GoDoctor tools: {godoctor_tools}")
        if used_shell:
             print(f"  -> MIXED USAGE (Shell + GoDoctor)")
        else:
             print(f"  -> PURE GoDoctor (No Shell)")
    # else:
    #     print(f"Run {run_id}: Shell only (or no relevant tools)")

conn.close()
