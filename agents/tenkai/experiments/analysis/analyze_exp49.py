import sqlite3
import json
import os

DB_PATH = 'agents/tenkai/experiments/tenkai.db'
EXP_ID = 49

def analyze_experiment():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print(f"--- Analyzing Experiment {EXP_ID} ---\n")

    # 1. Get Alternatives
    cursor.execute("SELECT DISTINCT alternative FROM run_results WHERE experiment_id = ?", (EXP_ID,))
    alternatives = [row['alternative'] for row in cursor.fetchall()]
    print(f"Alternatives found: {alternatives}\n")

    # 2. Tool Stats per Alternative
    print("--- Tool Usage Statistics ---")
    for alt in alternatives:
        print(f"\nAlternative: {alt}")
        query = """
            SELECT 
                json_extract(payload, '$.name') as tool_name,
                json_extract(payload, '$.status') as status,
                COUNT(*) as count
            FROM run_events e
            JOIN run_results r ON e.run_id = r.id
            WHERE r.experiment_id = ? AND r.alternative = ? AND e.type = 'tool'
            GROUP BY tool_name, status
            ORDER BY tool_name, status
        """
        cursor.execute(query, (EXP_ID, alt))
        rows = cursor.fetchall()
        if not rows:
            print("  (No tool usage found)")
            continue
        
        for row in rows:
            print(f"  {row['tool_name']:<20} {row['status']:<10}: {row['count']}")

    # 3. Deep Dive into Failures for Key Tools
    target_tools = ['file_edit', 'file_create', 'go_mod', 'go_build', 'go_get', 'cmd.run']
    
    print("\n\n--- Deep Dive: Failed Tool Calls ---")
    
    query_failures = """
        SELECT 
            r.alternative,
            r.scenario,
            r.repetition,
            json_extract(payload, '$.name') as tool_name,
            json_extract(payload, '$.args') as args,
            json_extract(payload, '$.error') as error,
            json_extract(payload, '$.output') as output
        FROM run_events e
        JOIN run_results r ON e.run_id = r.id
        WHERE r.experiment_id = ? 
          AND e.type = 'tool' 
          AND json_extract(payload, '$.status') != 'success'
          AND (
              json_extract(payload, '$.name') LIKE 'file_%' OR 
              json_extract(payload, '$.name') LIKE 'go_%' OR
              json_extract(payload, '$.name') = 'cmd.run'
          )
    """
    
    cursor.execute(query_failures, (EXP_ID,))
    failures = cursor.fetchall()

    if not failures:
        print("No failures found for target tools.")
    else:
        for fail in failures:
            print(f"\n[{fail['alternative']}] {fail['tool_name']}")
            print(f"  Args:   {fail['args']}")
            if fail['error']:
                print(f"  Error:  {fail['error']}")
            if fail['output']:
                # Truncate output if too long
                out = fail['output']
                if len(out) > 300:
                    out = out[:300] + "... [TRUNCATED]"
                print(f"  Output: {out.replace(chr(10), chr(10) + '          ')}")

    # 4. Pattern Analysis: file_edit "No Changes" or specific errors
    print("\n\n--- Pattern Analysis: file_edit issues ---")
    query_edit = """
        SELECT 
            r.alternative,
            json_extract(payload, '$.args') as args,
            json_extract(payload, '$.output') as output
        FROM run_events e
        JOIN run_results r ON e.run_id = r.id
        WHERE r.experiment_id = ? 
          AND json_extract(payload, '$.name') = 'file_edit'
    """
    cursor.execute(query_edit, (EXP_ID,))
    edits = cursor.fetchall()
    
    edit_issues = 0
    for edit in edits:
        output = edit['output'] or ""
        if "unable to locate" in output or "failed to find" in output or "Error" in output or "WARNING" in output:
            edit_issues += 1
            print(f"\n[{edit['alternative']}] file_edit Issue:")
            print(f"  Args: {edit['args']}")
            print(f"  Output: {output[:500].replace(chr(10), chr(10) + '          ')}")

    if edit_issues == 0:
        print("No obvious file_edit text search failures found.")

    conn.close()

if __name__ == "__main__":
    analyze_experiment()
