import sqlite3
import json
import os

DB_PATH = 'agents/tenkai/experiments/tenkai.db'
EXP_ID = 49

def extract_raw_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    query = """
        SELECT 
            r.alternative,
            json_extract(payload, '$.name') as tool_name,
            json_extract(payload, '$.args') as args,
            json_extract(payload, '$.status') as status,
            json_extract(payload, '$.error') as error,
            json_extract(payload, '$.output') as output
        FROM run_events e
        JOIN run_results r ON e.run_id = r.id
        WHERE r.experiment_id = ? 
          AND e.type = 'tool'
          AND (
              json_extract(payload, '$.status') != 'success' 
              OR json_extract(payload, '$.output') LIKE '%WARNING%'
              OR json_extract(payload, '$.output') LIKE '%Error%'
          )
        ORDER BY tool_name
    """
    
    cursor.execute(query, (EXP_ID,))
    rows = cursor.fetchall()

    for row in rows:
        print(f"TOOL: {row['tool_name']}")
        print(f"ALT:  {row['alternative']}")
        print(f"ARGS: {row['args']}")
        if row['error']:
            print(f"ERR:  {row['error']}")
        if row['output']:
            print(f"OUT:  {row['output']}")
        print("-" * 40)

    conn.close()

if __name__ == "__main__":
    extract_raw_data()
