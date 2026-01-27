# Tenkai Database Schema (`tenkai.db`)

The Tenkai database stores all experiment configurations, run execution logs, and result metrics. Use this reference to construct accurate SQL queries.

## Core Tables

### `experiments`
Stores high-level metadata about an experiment session.
- **`id`**: Primary Key (used in `run_results.experiment_id`).
- **`name`**: Human-readable name.
- **`config_content`**: The full YAML configuration used.

### `run_results`
The primary table for analysis. Each row represents a single execution (repetition) of a specific alternative in a specific scenario.
- **`id`**: Primary Key (Run ID).
- **`experiment_id`**: FK to `experiments`.
- **`alternative`**: The configuration variant name (e.g., "default", "godoctor-mcp").
- **`is_success`**: Boolean (1/0) indicating if validation passed.
- **`duration`**: Execution time in nanoseconds (Divide by `1e9` for seconds).
- **`total_tokens`**: Total LLM tokens consumed.
- **`tool_calls_count`**: Total number of tool calls made.
- **`failed_tool_calls`**: Count of tool calls that returned an error.
- **`status`**: "COMPLETED", "ABORTED", etc.
- **`reason`**: "SUCCESS", "FAILED (VALIDATION)", "FAILED (TIMEOUT)", etc.

### `run_events`
The raw event log stream for every run.
- **`run_id`**: FK to `run_results`.
- **`type`**: Event type ("tool", "message", "error").
- **`payload`**: JSON string containing the details.
    - For `tool`: `{"name": "...", "args": {...}, "output": "...", "status": "..."}`
    - For `message`: `{"role": "...", "content": "..."}`

## Views (Simplified Access)

### `tool_usage`
A convenience view over `run_events` filtered for `type='tool'`.
- **`run_id`**: Link to `run_results`.
- **`name`**: Tool name.
- **`args`**: JSON arguments.
- **`output`**: Tool output (stdout/stderr/error).
- **`status`**: "success" or "error".

## Common Queries

**1. Performance Summary by Alternative**
```sql
SELECT 
    alternative, 
    COUNT(*) as total, 
    SUM(is_success) as successes, 
    AVG(duration)/1e9 as avg_dur, 
    AVG(total_tokens) as avg_tok 
FROM run_results 
WHERE experiment_id = ? 
GROUP BY alternative;
```

**2. Tool Usage Stats**
```sql
SELECT 
    r.alternative,
    tu.name,
    COUNT(*) as count
FROM run_results r
JOIN tool_usage tu ON r.id = tu.run_id
WHERE r.experiment_id = ?
GROUP BY r.alternative, tu.name;
```
