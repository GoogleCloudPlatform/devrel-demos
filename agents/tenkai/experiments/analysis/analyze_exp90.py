import csv
import collections

# Define godoctor tools
GODOCTOR_TOOLS = {
    'add_dependency', 'file_create', 'list_files', 'read_docs', 
    'smart_edit', 'smart_read', 'verify_build', 'verify_tests', 
    'check_api', 'code_review', 'modernize_code'
}

# Data structures
runs = {} # run_id -> {alternative, is_success, duration, total_tokens, tools: set()}

# Load data
with open('agents/tenkai/experiments/analysis/exp90_raw_tools.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        run_id = row['run_id']
        if run_id not in runs:
            runs[run_id] = {
                'alternative': row['alternative'],
                'is_success': int(row['is_success']),
                'duration': float(row['duration']) / 1e9, # ns to s
                'total_tokens': int(row['total_tokens']),
                'tools': []
            }
        runs[run_id]['tools'].append(row['tool_name'])

# Analysis
results = collections.defaultdict(lambda: {
    'total_runs': 0,
    'godoctor_runs': 0,
    'godoctor_successes': 0,
    'godoctor_duration': [],
    'godoctor_tokens': [],
    'tool_usage': collections.Counter()
})

for run_id, data in runs.items():
    alt = data['alternative']
    
    # Check if run used ANY godoctor tool
    used_godoctor = any(t in GODOCTOR_TOOLS for t in data['tools'])
    
    results[alt]['total_runs'] += 1
    
    if used_godoctor:
        results[alt]['godoctor_runs'] += 1
        if data['is_success']:
            results[alt]['godoctor_successes'] += 1
        results[alt]['godoctor_duration'].append(data['duration'])
        results[alt]['godoctor_tokens'].append(data['total_tokens'])
        
        # Count tool usage for these runs
        for t in data['tools']:
            results[alt]['tool_usage'][t] += 1

# Generate Report
print("# Experiment 90: GoDoctor Tool Usage Analysis")
print("\nFilter: Runs that used at least one GoDoctor tool (smart_edit, read_docs, etc.)\n")

print("| Alternative | Total Runs | GD Runs | GD Success Rate | Avg Duration (s) | Avg Tokens |")
print("|---|---|---|---|---|---|")

for alt, stats in results.items():
    if stats['godoctor_runs'] == 0:
        print(f"| {alt} | {stats['total_runs']} | 0 | N/A | N/A | N/A |")
        continue
        
    avg_dur = sum(stats['godoctor_duration']) / stats['godoctor_runs']
    avg_tok = sum(stats['godoctor_tokens']) / stats['godoctor_runs']
    success_rate = (stats['godoctor_successes'] / stats['godoctor_runs']) * 100
    
    # Get top 3 GD tools
    gd_tools_counts = {k: v for k, v in stats['tool_usage'].items() if k in GODOCTOR_TOOLS}
    top_gd = sorted(gd_tools_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_gd_str = ", ".join([f"{k}({v})" for k, v in top_gd])
    
    print(f"| {alt} | {stats['total_runs']} | {stats['godoctor_runs']} | {success_rate:.1f}% | {avg_dur:.1f} | {avg_tok:.0f} | {top_gd_str} |")

print("\n## Adoption Rate")
for alt, stats in results.items():
    adoption = (stats['godoctor_runs'] / stats['total_runs']) * 100
    print(f"- **{alt}**: {adoption:.1f}% of runs used GoDoctor tools.")
