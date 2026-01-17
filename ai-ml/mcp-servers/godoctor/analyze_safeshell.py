
import sqlite3
import json
import textwrap

DB_PATH = '/Users/petruzalek/projects/devrel-demos/agents/tenkai/experiments/tenkai.db'
EXP_ID = 46

def analyze():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    # Total runs in experiment
    total_runs = cur.execute("SELECT count(*) FROM run_results WHERE experiment_id = ?", (EXP_ID,)).fetchone()[0]
    print(f"Total Runs in Experiment {EXP_ID}: {total_runs}")

    query = """
    SELECT 
        t.run_id, 
        t.args, 
        t.status, 
        t.error, 
        t.output 
    FROM tool_usage t 
    JOIN run_results r ON t.run_id = r.id 
    WHERE r.experiment_id = ? AND t.name = 'safe_shell'
    ORDER BY t.run_id ASC
    """
    
    rows = cur.execute(query, (EXP_ID,)).fetchall()
    print(f"Total safe_shell calls analyzed: {len(rows)}")
    
    categories = {
        "Schema Violation": 0,
        "Blocked Command": 0,
        "Server EOF": 0,
        "Trailing Data": 0,
        "Exit Status 1": 0,
        "Execution Error (Other)": 0,
        "Other Tool Error": 0,
        "Empty/Missing Output": 0,
        "Success": 0,
        "Other": 0
    }
    
    details = []

    for row in rows:
        run_id = row['run_id']
        args_raw = row['args']
        tool_status = row['status']
        tool_error = row['error']
        tool_output = row['output'] if row['output'] else ""
        
        if tool_error and "must have required property" in tool_error:
            categories["Schema Violation"] += 1
            details.append(f"Run {run_id}: Schema Violation - {tool_error}")
            continue

        # Check for blocked commands in ERROR or OUTPUT (sometimes it returns as a result)
        # CASE INSENSITIVE CHECK
        output_lower = tool_output.lower()
        error_lower = (tool_error or "").lower()
        
        if "blocked" in error_lower or "blocked" in output_lower:
            categories["Blocked Command"] += 1
            details.append(f"Run {run_id}: Blocked - {tool_error or tool_output.split('Status:')[0]}")
            continue

        if tool_error:
            categories["Other Tool Error"] += 1
            details.append(f"Run {run_id}: Tool Error - {tool_error}")
            continue

        # 2. Execution Result Parsing
        if "Status: Error" in tool_output:
            # Extract distinct error from output
            if "server is closing: eof" in output_lower:
                categories["Server EOF"] += 1
            elif "invalid trailing data" in output_lower:
                categories["Trailing Data"] += 1
            elif "exit status 1" in output_lower:
                categories["Exit Status 1"] += 1
                if "invalid character 'c'" in output_lower:
                    try:
                        args_obj = json.loads(row['args'])
                        stdin_sample = args_obj.get('stdin', '')[:50]
                        details.append(f"Run {run_id}: Invalid Char 'C' - Stdin starts with: {repr(stdin_sample)}")
                    except:
                        details.append(f"Run {run_id}: Invalid Char 'C' - (parse error)")
                else:
                    details.append(f"Run {run_id}: Generic Exit Status 1 - {tool_output[:200].replace(chr(10), ' ')}")
            else:
                categories["Execution Error (Other)"] += 1
                details.append(f"Run {run_id}: Other Exec Error - {tool_output[:100]}")
            continue

        if "Status: Success" in tool_output:
            # check for empty numeric output or similar issues if needed?
            # For now count as success unless we want to detect "Success but empty stdout"
            categories["Success"] += 1
            continue

        categories["Other"] += 1
        details.append(f"Run {run_id}: Unknown State - {tool_output[:50]}")

    print(f"\nAnalysis of Safe Shell Usage in Experiment {EXP_ID}")
    print("=" * 40)
    print(f"{'Category':<25} | {'Count':<5}")
    print("-" * 33)
    for cat, count in categories.items():
        print(f"{cat:<25} | {count:<5}")
    print("=" * 40)
    
    # Print distinct Exit Status 1 details to see what they are
    print("\nGeneric 'Exit Status 1' Details:")
    generic_errors = [d for d in details if "Generic Exit Status 1" in d]
    for d in generic_errors[:20]: # show first 20
        print(d)

    print("\nSample Details (First 10):")
    for d in details[:10]:
        print(d)

    
    # Run 1553 Check (Commented out to reduce noise, unless needed)
    # ...


    # Success Analysis
    # Define colors for output
    BOLD = "\033[1m"
    BLUE = "\033[94m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    RESET = "\033[0m"

    print(f"\n{BOLD}{BLUE}=== DEEP SEMANTIC ANALYSIS (Successes & False Positives) ==={RESET}")
    print("Sampling successful runs to see what the Agent *thought* happened...")

    # Join tool_usage with the NEXT event (presumably a message) to see agent reaction
    # We use a correlated subquery to find the next event
    cur.execute("""
        SELECT 
            t.run_id,
            t.id,
            t.args,
            t.output,
            (SELECT payload FROM run_events e2 
             WHERE e2.run_id = t.run_id 
             AND e2.id > t.id 
             AND e2.type IN ('message', 'model_response')
             ORDER BY e2.id ASC LIMIT 1) as next_message_payload
        FROM tool_usage t
        JOIN run_results r ON t.run_id = r.id
        WHERE t.name = 'safe_shell' 
        AND r.experiment_id = ?
        AND t.status = 'success'
        AND t.args LIKE '%./hello%'
        ORDER BY RANDOM()
        LIMIT 10;
    """, (EXP_ID,))

    success_samples = cur.fetchall()
    for row in success_samples:
        run_id, tool_id, args, output, next_msg = row
        print(f"\n{YELLOW}Run {run_id} (Tool Call {tool_id}){RESET}")
        
        # Parse Args
        try:
            arg_json = json.loads(args)
            cmd_args = arg_json.get('args', [])
            stdin = " ".join([a for a in cmd_args if '{' in a]) # Rough heuristic for stdin blob
            if len(stdin) > 100: stdin = stdin[:100] + "..."
            print(f"  Input: ./hello (Stdin: {stdin})")
        except:
            print(f"  Input: {args}")

        # Parse Output
        out_len = len(output) if output else 0
        out_preview = (output or "").replace('\n', ' ')
        if len(out_preview) > 200: out_preview = out_preview[:200] + "..."
        if out_len == 0:
            print(f"  {RED}Output: [EMPTY] (Length: 0){RESET}")
        else:
            print(f"  {GREEN}Output: {out_preview}{RESET}")

        # Parse Next Message (Agent Reaction)
        if next_msg:
            try:
                # payload might be just the text string or a JSON object depending on 'type'
                # run_events 'message' type usually has JSON payload with 'role' and 'content'
                msg_json = json.loads(next_msg)
                
                # Handle different payload shapes (tenkai specific)
                content = ""
                if isinstance(msg_json, dict):
                    content = msg_json.get('content', str(msg_json))
                else:
                    content = str(msg_json)
                
                # Extract text if it's a structured message
                if isinstance(content, list): # Block list
                    text_parts = [b.get('text', '') for b in content if b.get('type') == 'text']
                    content = " ".join(text_parts)
                
                clean_content = content.replace('\n', ' ')
                if len(clean_content) > 300: clean_content = clean_content[:300] + "..."
                
                print(f"  {CYAN}Agent Reaction: \"{clean_content}\"{RESET}")
            except Exception as e:
                print(f"  Agent Reaction (Parse Error): {e} | Raw: {next_msg[:100]}")
        else:
            print("  Agent Reaction: [None found]")

    print(f"\n{BOLD}{RED}=== DEEP SEMANTIC ANALYSIS (Failures & False Negatives) ==={RESET}")
    print("Sampling FAILED runs to see if Agent ignored valid output...")

    cur.execute("""
        SELECT 
            t.run_id,
            t.id,
            t.args,
            t.output,
            t.error,
            (SELECT payload FROM run_events e2 
             WHERE e2.run_id = t.run_id 
             AND e2.id > t.id 
             AND e2.type IN ('message', 'model_response')
             ORDER BY e2.id ASC LIMIT 1) as next_message_payload
        FROM tool_usage t
        JOIN run_results r ON t.run_id = r.id
        WHERE t.name = 'safe_shell' 
        AND r.experiment_id = ?
        AND t.status != 'success'
        AND t.args LIKE '%./hello%'
        ORDER BY RANDOM()
        LIMIT 10;
    """, (EXP_ID,))

    fail_samples = cur.fetchall()
    for row in fail_samples:
        run_id, tool_id, args, output, error, next_msg = row
        print(f"\n{RED}Run {run_id} (Tool Call {tool_id}){RESET}")
        
        # Parse Args
        try:
            arg_json = json.loads(args)
            cmd_args = arg_json.get('args', [])
            stdin = " ".join([a for a in cmd_args if '{' in a]) 
            if len(stdin) > 100: stdin = stdin[:100] + "..."
            print(f"  Input: ./hello (Stdin: {stdin})")
        except:
            print(f"  Input: {args}")

        # Error
        print(f"  Error: {error}")

        # Parse Output (Check for valid JSON hidden in error)
        out_len = len(output) if output else 0
        out_preview = (output or "").replace('\n', ' ')
        if len(out_preview) > 200: out_preview = out_preview[:200] + "..."
        
        has_json = "{" in (output or "") and "}" in (output or "")
        
        if out_len == 0:
            print(f"  Output: [EMPTY]")
        else:
            color = GREEN if has_json else RED
            print(f"  Output: {color}{out_preview}{RESET}")
            if has_json:
                print(f"  {BOLD}{GREEN}>>> POTENTIAL VALID JSON FOUND IN OUTPUT! <<<{RESET}")

        # Parse Next Message (Agent Reaction)
        if next_msg:
            try:
                msg_json = json.loads(next_msg)
                content = ""
                if isinstance(msg_json, dict):
                    content = msg_json.get('content', str(msg_json))
                else:
                    content = str(msg_json)
                
                if isinstance(content, list): 
                    text_parts = [b.get('text', '') for b in content if b.get('type') == 'text']
                    content = " ".join(text_parts)
                
                clean_content = content.replace('\n', ' ')
                if len(clean_content) > 300: clean_content = clean_content[:300] + "..."
                
                print(f"  {CYAN}Agent Reaction: \"{clean_content}\"{RESET}")
            except Exception as e:
                print(f"  Agent Reaction (Parse Error): {e}")
        else:
            print("  Agent Reaction: [None found]")

if __name__ == "__main__":
    analyze()
