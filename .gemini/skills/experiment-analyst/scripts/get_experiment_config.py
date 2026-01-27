import sqlite3
import sys

def get_config(exp_id):
    conn = sqlite3.connect('agents/tenkai/experiments/tenkai.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, config_content FROM experiments WHERE id = ?", (exp_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"Experiment {exp_id} not found.")
        return

    name, config_content = row
    print(f"Experiment: {name} (ID: {exp_id})\n")
    print("--- Configuration ---")
    print(config_content)
    
    # Optional: Parse YAML to highlight key differences?
    # For now, raw YAML is good enough for the LLM to interpret.

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 get_experiment_config.py <EXP_ID>")
        sys.exit(1)
    
    get_config(sys.argv[1])
