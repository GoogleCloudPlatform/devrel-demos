import csv
import collections

# Define tool categories
GODOCTOR_TOOLS = {
    'add_dependency', 'file_create', 'list_files', 'read_docs', 
    'smart_edit', 'smart_read', 'verify_build', 'verify_tests', 
    'check_api', 'code_review', 'modernize_code'
}

SHELL_TOOLS = {'run_shell_command'}

results = collections.defaultdict(lambda: collections.Counter())

with open('agents/tenkai/experiments/analysis/exp91_tool_usage.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        alt = row['alternative']
        tool = row['tool_name']
        count = int(row['count'])
        results[alt][tool] = count

print("# Experiment 91: Tool Usage Analysis")
print("\n| Alternative | Total Calls | Shell Calls (%) | GoDoctor Calls (%) | Other Calls (%) | Top 3 Tools |")
print("|---|---|---|---|---|---|")

for alt, counts in results.items():
    total = sum(counts.values())
    if total == 0:
        continue
    
    shell_count = sum(counts[t] for t in SHELL_TOOLS if t in counts)
    gd_count = sum(counts[t] for t in GODOCTOR_TOOLS if t in counts)
    other_count = total - shell_count - gd_count
    
    shell_pct = (shell_count / total) * 100
    gd_pct = (gd_count / total) * 100
    other_pct = (other_count / total) * 100
    
    top_3 = ", ".join([f"{t}({c})" for t, c in counts.most_common(3)])
    
    print(f"| {alt} | {total} | {shell_pct:.1f}% | {gd_pct:.1f}% | {other_pct:.1f}% | {top_3} |")
