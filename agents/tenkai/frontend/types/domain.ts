export interface ExperimentRecord {
    id: number;
    name: string;
    description?: string;
    timestamp: string;
    status: 'running' | 'ABORTED' | 'completed' | 'RUNNING' | 'COMPLETED';
    reps: number;
    concurrent: number;
    is_locked?: boolean;

    error_message?: string;
    experiment_control?: string;
    ai_analysis?: string;
    success_rate?: number;
    avg_duration?: number;
    avg_tokens?: number;
    total_lint?: number;
    successful_runs?: number;
    config_path?: string;
    results_path?: string;
    report_path?: string;
    config_content?: string;
    report_content?: string;
    execution_control?: string;
    total_jobs?: number;
    completed_jobs?: number;
    num_alternatives?: number;
    timeout?: string;
    progress?: {
        completed: number;
        total: number;
        percentage: number;
    };
}

export interface Checkpoint {
    experiment_id?: number | string;
    status: string;
    total_jobs: number;
    completed_jobs: number;
    percentage: number;
    last_update?: string;
}

export interface ExperimentSummaryRow {
    id: number;
    experiment_id: number;
    alternative: string;
    total_runs: number;
    success_count: number;
    success_rate: number;
    avg_duration: number;
    avg_tokens: number;
    avg_lint: number;
    avg_tests_passed: number;
    avg_tests_failed: number;
    timeouts: number;
    total_tool_calls: number;
    failed_tool_calls: number;
    p_success?: number;
    p_duration?: number;
    p_tokens?: number;
    p_lint?: number;
    p_tests_passed?: number;
    p_tests_failed?: number;
    p_timeout?: number;
    p_tool_calls?: number;
}

export interface Alternative {
    name: string;
    description?: string;
    command: string;
    args: string[];
    env?: Record<string, string>;
    settings?: Record<string, any>;
    system_prompt?: string;
    context?: string;
}

export interface RunResult {
    id: number;
    experiment_id: number;
    alternative: string;
    scenario: string;
    repetition: number;
    duration: number;
    error?: string;
    tests_passed: number;
    tests_failed: number;
    lint_issues: number;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    tool_calls_count: number;
    loop_detected: boolean;
    stdout?: string;
    stderr?: string;
    is_success: boolean;
    validation_report?: string;
    reason?: string;
    status: string;
}

