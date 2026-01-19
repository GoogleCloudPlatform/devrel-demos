import sqlite3
import json
from collections import Counter

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63
ALT_V1 = "godoctor-advanced-no-core"
ALT_V2 = "godoctor-advanced-safe-shell-v2"

def get_runs(cursor, alt):
    cursor.execute("""
        SELECT id, is_success, reason, validation_report
        FROM run_results 
        WHERE experiment_id = ? AND alternative = ?
    """, (EXP_ID, alt))
    return cursor.fetchall()

def get_safe_shell_trace(cursor, run_id):
    cursor.execute("""
        SELECT type, payload
        FROM run_events
        WHERE run_id = ?
        ORDER BY id ASC
    """, (run_id,))
    events = cursor.fetchall()
    
    trace = []
    for evt in events:
        payload = json.loads(evt['payload'])
        
        if evt['type'] == 'tool' and payload.get('name') == 'safe_shell':
            args = payload.get('args')
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except:
                    pass
            trace.append({
                "type": "call",
                "command": args.get('command') if isinstance(args, dict) else "???",
                "args": args.get('args') if isinstance(args, dict) else []
            })
            
        elif evt['type'] == 'result':
            # This is a simplification; in a real trace we match ID. 
            # But here we just look for significant keywords in ANY result 
            # (which usually follows the tool call).
            output = payload.get('output', '')
            if output:
                status = "OK"
                if "Blocked" in output: status = "BLOCKED"
                elif "Permission Denied" in output: status = "DENIED"
                elif "Error" in output: status = "ERROR"
                elif "Advice" in output: status = "ADVICE"
                
                if status != "OK":
                     trace.append({
                        "type": "output",
                        "status": status,
                        "content": output[:200]
                    })
    return trace

def analyze():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"--- Deep Dive Analysis: Exp {EXP_ID} ---")
    
    # 1. Compare Failure Reasons
    print("\n=== Failure Reason Distribution ===")
    for alt in [ALT_V1, ALT_V2]:
        runs = get_runs(cursor, alt)
        reasons = Counter([r['reason'] for r in runs if not r['is_success']])
        total = len(runs)
        success = sum(1 for r in runs if r['is_success'])
        print(f"\n{alt}:")
        print(f"  Total: {total}, Success: {success} ({success/total:.1%})")
        print("  Failure Reasons:")
        for r, c in reasons.items():
            print(f"    - {r}: {c}")

    # 2. Deep Dive into V2 Failures
    print(f"\n\n=== {ALT_V2} Failure Analysis ===")
    v2_runs = get_runs(cursor, ALT_V2)
    failed_v2 = [r for r in v2_runs if not r['is_success']]
    
    for run in failed_v2:
        print(f"\nRun {run['id']} ({run['reason']}):")
        
        # Validation Info
        if run['validation_report']:
            try:
                rep = json.loads(run['validation_report'])
                for item in rep.get('items', []):
                    if not item.get('success'):
                        print(f"  [VALIDATION FAIL] {item.get('description')}")
            except:
                pass

        # Shell Trace
        trace = get_safe_shell_trace(cursor, run['id'])
        if not trace:
            print("  (No safe_shell calls)")
        else:
            for t in trace:
                if t['type'] == 'call':
                    print(f"  > safe_shell: {t['command']} {t['args']}")
                else:
                    print(f"    -> {t['status']}: {t['content']}")

    # 3. Check V2 Successes for "Recovered" Blocks
    print(f"\n\n=== {ALT_V2} Recovered Blocks (Successes) ===")
    success_v2 = [r for r in v2_runs if r['is_success']]
    recovered_count = 0
    
    for run in success_v2:
        trace = get_safe_shell_trace(cursor, run['id'])
        has_block = any(t['type'] == 'output' and t['status'] in ['BLOCKED', 'DENIED'] for t in trace)
        if has_block:
            recovered_count += 1
            print(f"\nRun {run['id']} (Success):")
            for t in trace:
                 if t['type'] == 'output' and t['status'] in ['BLOCKED', 'DENIED']:
                     print(f"    Encountered {t['status']}")
    
    print(f"\nTotal Successes with Blocks: {recovered_count}")

    conn.close()

if __name__ == "__main__":
    analyze()
