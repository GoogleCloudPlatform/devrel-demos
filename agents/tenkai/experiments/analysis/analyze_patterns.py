import sqlite3
import json
import argparse
from collections import defaultdict

# Default Configuration
DB_PATH = "agents/tenkai/experiments/tenkai.db"

def analyze(experiment_id, alternative):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get runs
    cursor.execute("""
        SELECT id, is_success 
        FROM run_results 
        WHERE experiment_id = ? AND alternative = ?
    """, (experiment_id, alternative))
    runs = cursor.fetchall()

    patterns = []
    
    for run_id, is_success in runs:
        # Get events including TYPE to distinguish messages from tools
        cursor.execute("SELECT type, payload FROM run_events WHERE run_id = ? ORDER BY id", (run_id,))
        events = cursor.fetchall()
        
        current_thought = []
        workflow = []
        
        for etype, payload_str in events:
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                continue
            
            if etype == "message":
                role = payload.get("role")
                content = payload.get("content", "")
                if role in ["model", "assistant"]:
                    current_thought.append(content)
            
            elif etype == "tool":
                tool_name = payload.get("name")
                tool_args = payload.get("args")
                tool_output = payload.get("output", "")
                
                thought = "".join(current_thought).strip()
                
                workflow.append({
                    "thought": thought,
                    "tool": tool_name,
                    "args": tool_args,
                    "output": tool_output
                })
                
                current_thought = [] # Reset for next step
        
        patterns.append({
            "run_id": run_id,
            "is_success": is_success,
            "workflow": workflow
        })

    conn.close()
    return patterns

def summarize(patterns, alternative):
    print(f"Analyzing {len(patterns)} runs for {alternative}...")
    
    tool_transitions = defaultdict(int)
    
    for p in patterns:
        wf = p["workflow"]
        prev_tool = "START"
        for step in wf:
            tool = step["tool"]
            tool_transitions[(prev_tool, tool)] += 1
            prev_tool = tool
        tool_transitions[(prev_tool, "END")] += 1

    print("\n--- Common Tool Transitions ---")
    sorted_trans = sorted(tool_transitions.items(), key=lambda x: x[1], reverse=True)
    for (prev, curr), count in sorted_trans[:20]:
        print(f"{prev:20} -> {curr:20} : {count}")

    print("\n--- Example Workflows (First 3 Successful) ---")
    success_count = 0
    for p in patterns:
        if p["is_success"] and success_count < 3:
            print(f"\nRun ID: {p['run_id']} (SUCCESS)")
            for i, step in enumerate(p["workflow"]):
                print(f"  Step {i+1}:")
                if step['thought']:
                    print(f"    Thought: {step['thought'][:100]}...")
                print(f"    Tool:    {step['tool']}({step['args']})")
            success_count += 1

    print("\n--- Failure Deep Dive (First 3 Failed) ---")
    fail_count = 0
    for p in patterns:
        if not p["is_success"] and fail_count < 3:
            print(f"\nRun ID: {p['run_id']} (FAILED)")
            for i, step in enumerate(p["workflow"]):
                print(f"  Step {i+1}:")
                if step['thought']:
                    print(f"    Thought: {step['thought'][:100]}...")
                print(f"    Tool:    {step['tool']}({step['args']})")
                if step['output'] and ('error' in step['output'].lower() or 'failed' in step['output'].lower()):
                     print(f"    Output:  [ERROR/FAIL DETECTED] {step['output'][:200]}...")
            fail_count += 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze Tenkai experiment patterns.")
    parser.add_argument("experiment_id", type=int, help="The ID of the experiment to analyze.")
    parser.add_argument("alternative", type=str, help="The name of the alternative to analyze.")
    args = parser.parse_args()

    data = analyze(args.experiment_id, args.alternative)
    summarize(data, args.alternative)
