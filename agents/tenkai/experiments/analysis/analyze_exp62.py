import sqlite3
import json
import statistics

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63

def analyze():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    alternatives = ["godoctor-advanced-no-core", "godoctor-advanced-safe-shell-v2"]
    
    print(f"--- Analysis for Experiment {EXP_ID} ---\n")

    for alt in alternatives:
        print(f"=== Alternative: {alt} ===")
        
        # 1. Success & Duration
        cursor.execute("""
            SELECT is_success, duration, tool_calls_count 
            FROM run_results 
            WHERE experiment_id = ? AND alternative = ? AND status = 'COMPLETED'
        """, (EXP_ID, alt))
        runs = cursor.fetchall()
        
        if not runs:
            print("No runs found.")
            continue

        success_count = sum(1 for r in runs if r[0])
        durations = [r[1] for r in runs if r[1] is not None]
        tool_counts = [r[2] for r in runs if r[2] is not None]
        
        avg_duration = statistics.mean(durations) / 1000000000.0 if durations else 0
        avg_tools = statistics.mean(tool_counts) if tool_counts else 0
        
        print(f"Runs: {len(runs)}")
        print(f"Success Rate: {success_count/len(runs):.1%}")
        print(f"Avg Duration: {avg_duration:.2f}s")
        print(f"Avg Tool Calls: {avg_tools:.1f}")

        # 2. Safe Shell Usage
        # Note: The payload structure is {"name": "safe_shell", "args": "{\"command\": ...}"}
        # SQLite's json_extract can parse nested JSON if valid, but here 'args' is a stringified JSON.
        # We need to extract 'args' string first, then parse it in Python? 
        # Or simplistic: json_extract(json_extract(payload, '$.args'), '$.command') might work if sqlite supports auto-unquote? 
        # Usually it doesn't.
        # Let's select the raw 'args' field and parse in Python.
        
        cursor.execute("""
            SELECT json_extract(t.payload, '$.args'), json_extract(t.payload, '$.output')
            FROM run_events t 
            JOIN run_results r ON t.run_id = r.id 
            WHERE r.experiment_id = ? AND r.alternative = ? AND json_extract(t.payload, '$.name') = 'safe_shell'
        """, (EXP_ID, alt))
        shell_calls_raw = cursor.fetchall()
        
        print(f"Total safe_shell calls: {len(shell_calls_raw)}")
        
        # Analyze Blocks/Advice (V2 specific)
        blocked = 0
        advised = 0
        rm_attempts = 0
        
        unique_cmds = {}

        for args_str, output in shell_calls_raw:
            try:
                # args_str is sometimes a dict (if pre-parsed) or string. 
                # Tenkai usually stores args as stringified JSON for tools?
                # Let's try to load it.
                if isinstance(args_str, str):
                    tool_args = json.loads(args_str)
                else:
                    tool_args = args_str # It's already an object?
                
                cmd = tool_args.get('command', 'UNKNOWN')
                args = tool_args.get('args', [])
            except:
                cmd = "PARSE_ERROR"
                args = []

            cmd_str = f"{cmd} {args}"
            unique_cmds[cmd_str] = unique_cmds.get(cmd_str, 0) + 1
            
            if output:
                if "Blocked:" in output or "Permission Denied" in output:
                    blocked += 1
                if "[ADVICE]:" in output:
                    advised += 1
            
            if cmd == "rm":
                rm_attempts += 1

        print(f"Blocked Calls: {blocked}")
        print(f"Advisory Calls: {advised}")
        print(f"RM Attempts: {rm_attempts}")
        
        print("Top 5 Commands:")
        sorted_cmds = sorted(unique_cmds.items(), key=lambda x: x[1], reverse=True)[:5]
        for c, count in sorted_cmds:
            print(f"  {count}x: {c}")

        # 3. Tool Failures
        cursor.execute("""
            SELECT json_extract(payload, '$.name'), count(*)
            FROM run_events t
            JOIN run_results r ON t.run_id = r.id
            WHERE r.experiment_id = ? AND r.alternative = ? 
            AND json_extract(t.payload, '$.status') = 'error'
            GROUP BY 1
            ORDER BY 2 DESC
        """, (EXP_ID, alt))
        failures = cursor.fetchall()
        
        print("Top Tool Failures:")
        for tool, count in failures:
            print(f"  {tool}: {count}")
            
        print("\n")
        
        # 4. Trace Analysis for RM
        print("=== Deep Dive: Why 'rm'? ===")
        # Get all runs that had safe_shell calls
        cursor.execute("""
            SELECT DISTINCT t.run_id
            FROM run_events t 
            JOIN run_results r ON t.run_id = r.id 
            WHERE r.experiment_id = ? AND r.alternative = ? 
            AND json_extract(t.payload, '$.name') = 'safe_shell'
        """, (EXP_ID, alt))
        candidate_runs = cursor.fetchall()
        
        for (run_id,) in candidate_runs:
            cursor.execute("""
                SELECT type, payload 
                FROM run_events 
                WHERE run_id = ? 
                ORDER BY id
            """, (run_id,))
            events = cursor.fetchall()
            
            for i, (evt_type, payload) in enumerate(events):
                if evt_type == 'tool':
                    try:
                        p = json.loads(payload)
                        if p.get('name') == 'safe_shell':
                            args_raw = p.get('args')
                            if isinstance(args_raw, str):
                                tool_args = json.loads(args_raw)
                            else:
                                tool_args = args_raw
                            
                            if tool_args.get('command') == 'rm':
                                # FOUND RM
                                # Get Previous Message (Reasoning)
                                prev_msg = "N/A"
                                for j in range(i-1, -1, -1):
                                    if events[j][0] == 'message':
                                        try:
                                            content = json.loads(events[j][1])
                                            # Gemini API structure: candidate.content.parts[0].text
                                            # Tenkai Parser structure: role, content (string or list)
                                            # Let's handle string content which is common in Tenkai views
                                            raw_content = content.get('content')
                                            if isinstance(raw_content, str):
                                                prev_msg = raw_content[:200]
                                            elif isinstance(raw_content, list):
                                                prev_msg = str(raw_content[0])[:200]
                                        except:
                                            prev_msg = "Parse Error"
                                        break
                                
                                print(f"Run {run_id}:")
                                print(f"  Reasoning: {prev_msg}")
                                print(f"  Action: rm {tool_args.get('args')}")
                                print("")
                    except:
                        continue

    conn.close()

if __name__ == "__main__":
    analyze()
