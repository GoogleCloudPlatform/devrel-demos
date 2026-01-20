import sqlite3
import json
import statistics
from collections import defaultdict

DB_PATH = "agents/tenkai/experiments/tenkai.db"
EXP_ID = 63

def get_run_details(cursor, run_id):
    cursor.execute("""
        SELECT type, payload 
        FROM run_events 
        WHERE run_id = ? 
        ORDER BY id ASC
    """, (run_id,))
    events = cursor.fetchall()
    
    turns = 0
    tool_outputs_len = 0
    tool_counts = defaultdict(int)
    
    # Track context growth
    input_tokens_trajectory = []
    
    for evt_type, payload_json in events:
        try:
            payload = json.loads(payload_json)
        except:
            continue
            
        if evt_type == 'model': # Model response
            turns += 1
        
        if evt_type == 'result': # Run Result (contains stats)
            stats = payload.get('stats', {})
            if stats.get('input_tokens'):
                input_tokens_trajectory.append(stats['input_tokens'])

        # Tool Usage analysis
        if evt_type == 'tool' or (evt_type == 'tool_use' and 'name' in payload): 
            # Normalizing event types (Tenkai vs Gemini parser differences)
            # In Tenkai DB, 'tool' usually has the output too.
            name = payload.get('name') or payload.get('tool_name')
            if name:
                tool_counts[name] += 1
            
            output = payload.get('output', '')
            if output:
                tool_outputs_len += len(output)
        
        # Also check 'tool_result' if separated
        if evt_type == 'tool_result':
            output = payload.get('output', '')
            # payload might differ slightly
            if isinstance(output, str):
                tool_outputs_len += len(output)
            elif isinstance(payload.get('content'), list):
                 # Handle multi-part content
                 for part in payload['content']:
                     if part.get('type') == 'text':
                         tool_outputs_len += len(part.get('text', ''))

    avg_input_tokens = statistics.mean(input_tokens_trajectory) if input_tokens_trajectory else 0
    start_tokens = input_tokens_trajectory[0] if input_tokens_trajectory else 0
    end_tokens = input_tokens_trajectory[-1] if input_tokens_trajectory else 0
    
    return {
        "turns": turns,
        "tool_output_chars": tool_outputs_len,
        "avg_input_tokens": avg_input_tokens,
        "context_growth": end_tokens - start_tokens,
        "tool_counts": tool_counts
    }

def analyze():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get alternatives
    cursor.execute("SELECT DISTINCT alternative FROM run_results WHERE experiment_id = ?", (EXP_ID,))
    alts = [row[0] for row in cursor.fetchall()]

    print(f"{'Alternative':<35} | {'Turns':<6} | {'Tool Out (Chars)':<16} | {'Context Growth':<14} | {'Top Tools'}")
    print("-" * 120)

    for alt in alts:
        # Get all COMPLETED runs for this alt
        cursor.execute("SELECT id FROM run_results WHERE experiment_id = ? AND alternative = ? AND status = 'COMPLETED'", (EXP_ID, alt))
        run_ids = [row[0] for row in cursor.fetchall()]
        
        if not run_ids: continue
        
        # Aggregate metrics
        total_turns = []
        total_tool_chars = []
        total_growth = []
        agg_tool_counts = defaultdict(int)
        
        for rid in run_ids:
            data = get_run_details(cursor, rid)
            total_turns.append(data['turns'])
            total_tool_chars.append(data['tool_output_chars'])
            total_growth.append(data['context_growth'])
            for t, c in data['tool_counts'].items():
                agg_tool_counts[t] += c
        
        avg_turns = statistics.mean(total_turns)
        avg_tool_chars = statistics.mean(total_tool_chars)
        avg_growth = statistics.mean(total_growth)
        
        # Top 3 tools
        top_tools = sorted(agg_tool_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_tools_str = ", ".join([f"{t}({c})" for t, c in top_tools])

        print(f"{alt:<35} | {avg_turns:<6.1f} | {avg_tool_chars:<16.0f} | {avg_growth:<14.0f} | {top_tools_str}")

    conn.close()

if __name__ == "__main__":
    analyze()
