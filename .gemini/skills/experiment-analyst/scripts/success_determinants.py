import sqlite3
import json
import collections
import sys
import os
import math

# Default Configuration
DEFAULT_DB_PATH = "agents/tenkai/experiments/tenkai.db"

def get_db_path():
    return os.environ.get("TENKAI_DB_PATH", DEFAULT_DB_PATH)

def analyze_success_determinants(exp_id):
    db_path = get_db_path()
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Fetch all runs with their outcome and tool usage
    # We aggregate tool usage per run
    cursor.execute("""
        SELECT 
            r.id,
            r.alternative,
            r.is_success,
            re.payload
        FROM run_results r
        JOIN run_events re ON r.id = re.run_id
        WHERE r.experiment_id = ? AND re.type = 'tool'
    """, (exp_id,))

    # Data structure:
    # alt_stats[alternative]['tools'][tool_name] = {success_runs: set(), fail_runs: set()}
    # alt_stats[alternative]['total_success'] = N
    # alt_stats[alternative]['total_fail'] = N
    
    alt_stats = collections.defaultdict(lambda: {
        'tools': collections.defaultdict(lambda: {'success': set(), 'fail': set()}),
        'runs': {'success': set(), 'fail': set()}
    })

    rows = cursor.fetchall()
    if not rows:
        print("No tool usage data found for this experiment.")
        return

    for run_id, alt, is_success, payload_json in rows:
        try:
            payload = json.loads(payload_json)
            tool_name = payload.get('name')
            if not tool_name: continue
            
            outcome = 'success' if is_success else 'fail'
            
            alt_stats[alt]['runs'][outcome].add(run_id)
            alt_stats[alt]['tools'][tool_name][outcome].add(run_id)
            
        except json.JSONDecodeError:
            continue

    print(f"## 4. Success Determinants Analysis\n")
    print("Which tools correlate with success (or failure)?\n")

    for alt, data in alt_stats.items():
        n_success = len(data['runs']['success'])
        n_fail = len(data['runs']['fail'])
        total_runs = n_success + n_fail
        
        if total_runs < 5: 
            print(f"### {alt}: Not enough data for correlation analysis ({total_runs} runs)\n")
            continue
            
        print(f"### {alt} (Success: {n_success}, Fail: {n_fail})")
        print("| Tool | Used in Success % | Used in Fail % | Correlation | Impact |")
        print("|---|---|---|---|---|")
        
        tool_metrics = []
        
        for tool, counts in data['tools'].items():
            used_in_success = len(counts['success'])
            used_in_fail = len(counts['fail'])
            
            succ_pct = (used_in_success / n_success * 100) if n_success > 0 else 0
            fail_pct = (used_in_fail / n_fail * 100) if n_fail > 0 else 0
            
            # Simple Phi Coefficient (Correlation) approximation
            # Or just difference in usage frequency
            diff = succ_pct - fail_pct
            
            # Label
            impact = "Neutral"
            if diff > 30: impact = "✅ Strong Success Driver"
            elif diff > 15: impact = "✅ Success Driver"
            elif diff < -30: impact = "❌ Strong Failure Signal"
            elif diff < -15: impact = "❌ Failure Signal"
            
            tool_metrics.append((tool, succ_pct, fail_pct, diff, impact))
            
        # Sort by absolute difference impact
        tool_metrics.sort(key=lambda x: abs(x[3]), reverse=True)
        
        for tool, succ, fail, diff, impact in tool_metrics:
            if abs(diff) < 10: continue # Filter noise
            print(f"| {tool} | {succ:.0f}% | {fail:.0f}% | {diff:+.0f}% | {impact} |")
        print("")

    conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 success_determinants.py <EXP_ID>")
        sys.exit(1)
    
    analyze_success_determinants(sys.argv[1])
