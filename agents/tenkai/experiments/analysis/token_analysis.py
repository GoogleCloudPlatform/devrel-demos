import sqlite3
import statistics

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63

def analyze():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all alternatives
    cursor.execute("SELECT DISTINCT alternative FROM run_results WHERE experiment_id = ?", (EXP_ID,))
    alts = [row[0] for row in cursor.fetchall()]

    print(f"{'Alternative':<35} | {'Avg Total':<10} | {'Avg Input':<10} | {'Avg Output':<10} | {'Tool Def Overhead (Est)'}")
    print("-" * 90)

    for alt in alts:
        cursor.execute("""
            SELECT 
                json_extract(t.payload, '$.stats.total_tokens'),
                json_extract(t.payload, '$.stats.input_tokens'),
                json_extract(t.payload, '$.stats.output_tokens'),
                count(*)
            FROM run_events t 
            JOIN run_results r ON t.run_id = r.id 
            WHERE r.experiment_id = ? AND r.alternative = ? AND t.type = 'result'
        """, (EXP_ID, alt))
        
        data = cursor.fetchall()
        if not data: continue
        
        totals = [row[0] for row in data if row[0]]
        inputs = [row[1] for row in data if row[1]]
        outputs = [row[2] for row in data if row[2]]
        count = len(totals)

        avg_total = statistics.mean(totals) if totals else 0
        avg_input = statistics.mean(inputs) if inputs else 0
        avg_output = statistics.mean(outputs) if outputs else 0
        
        # Estimate per-turn overhead differences relative to 'default'
        # This is rough, but illustrative.
        print(f"{alt:<35} | {avg_total:<10.0f} | {avg_input:<10.0f} | {avg_output:<10.0f} |")

    conn.close()

if __name__ == "__main__":
    analyze()
