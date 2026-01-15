import { notFound } from "next/navigation";

const API_BASE = '/api';

export interface ExperimentRecord {
    id: number;
    name: string;
    description: string;
    timestamp: string;
    status: string;
    reps: number;
    concurrent: number;
    total_jobs: number;
    completed_jobs: number;
    completion_percentage: number;
    is_locked: boolean;
    success_rate: number;
    avg_duration: number;
    avg_tokens: number;
    total_lint: number;
    successful_runs: number;
    timeout: string;
    error_message: string;
    config_content: string;
    ai_analysis: string;
    progress?: {
        completed: number;
        total: number;
        percentage: number;
    };
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
    p_success: number;
    p_duration: number;
    p_tokens: number;
    p_lint: number;
    p_tests_passed: number;
    p_tests_failed: number;
    p_timeout: number;
    p_tool_calls: number;
    tool_analysis: ToolAnalysis[];
}

export interface ToolAnalysis {
    tool_name: string;
    succ_fail_p_value: number;
    duration_corr: number;
    tokens_corr: number;
}

export interface RunResultRecord {
    id: number;
    experiment_id: number;
    alternative: string;
    scenario: string;
    repetition: number;
    duration: number;
    error: string;
    tests_passed: number;
    tests_failed: number;
    lint_issues: number;
    total_tokens: number;
    input_tokens: number;
    output_tokens: number;
    tool_calls_count: number;
    failed_tool_calls: number;
    loop_detected: boolean;
    status: string;
    reason: string;
    stdout: string;
    stderr: string;
    is_success: boolean;
    validation_report: string;
}

export interface ToolUsageRecord {
    id: number;
    run_id: number;
    name: string;
    args: string;
    status: string;
    output: string;
    error: string;
    duration: number;
    timestamp: string;
}

export interface MessageRecord {
    id: number;
    run_id: number;
    role: string;
    content: string;
    timestamp: string;
}

export interface TestResultRecord {
    id: number;
    run_id: number;
    name: string;
    status: string;
    duration_ns: number;
    output: string;
}

export interface LintResultRecord {
    id: number;
    run_id: number;
    file: string;
    line: number;
    col: number;
    message: string;
    severity: string;
    rule_id: string;
}

export interface Checkpoint {
    completed: number;
    total: number;
    percentage: number;
}

export interface Scenario {
    id: string; // ID is name in scenario.yaml usually, but looking at routes it might be handling IDs.
    name: string;
    description: string;
    locked: boolean;
    task: string;
    // ... assets, validation
}

export interface Template {
    id: string;
    name: string;
    description: string;
    locked: boolean;
    // ... config
}

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    // Check if we are checking "local" build or really client side?
    // If client side, relative path is fine.
    // If server side (build time), we might need absolute URL if backend is needed.
    // Assuming client side mostly.
    const res = await fetch(`${API_BASE}${endpoint}`, options);
    if (!res.ok) {
        throw new Error(`API Error ${res.status}: ${res.statusText}`);
    }
    return res.json();
}

export async function getExperiments(): Promise<ExperimentRecord[]> {
    return fetchAPI('/experiments');
}

export async function getExperiment(id: string | number): Promise<ExperimentRecord> {
    return fetchAPI(`/experiments/${id}`);
}

export async function getExperimentSummaries(id: string | number): Promise<ExperimentSummaryRow[]> {
    return fetchAPI(`/experiments/${id}/summaries`);
}

export async function getRunResults(id: string | number): Promise<RunResultRecord[]> {
    return fetchAPI(`/experiments/${id}/runs`);
}

export async function getScenarios(): Promise<Scenario[]> {
    return fetchAPI('/scenarios');
}

export async function getTemplates(): Promise<Template[]> {
    return fetchAPI('/templates');
}

export async function getSimplifiedMetrics(id: string | number): Promise<any> {
    // Based on route /tool-stats or similar? Or /stats?
    // The error log mentioned usage in [id]/page.tsx.
    // Let's assume it calls /tool-stats or just returns a part of ExperimentRecord?
    // I'll map it to /tool-stats for now.
    return fetchAPI(`/experiments/${id}/tool-stats`);
}

// Helper for checkpoint (progress)
export async function getCheckpoint(id: string | number): Promise<Checkpoint> {
    // Often part of experiment data, but if requested separately:
    const exp = await getExperiment(id);
    return exp.progress || { completed: 0, total: 0, percentage: 0 };
}

export async function lockExperiment(id: string | number): Promise<void> {
    await fetchAPI(`/experiments/${id}/lock`, { method: 'POST' });
}

export async function reValidateExperiment(id: string | number): Promise<void> {
    await fetchAPI(`/experiments/${id}/reval`, { method: 'POST' });
}

export async function reValidateRun(id: string | number): Promise<void> {
    await fetchAPI(`/runs/${id}/reval`, { method: 'POST' });
}

export async function lockScenario(id: string | number): Promise<void> {
    await fetchAPI(`/scenarios/${id}/lock`, { method: 'POST' });
}

export async function lockTemplate(id: string | number): Promise<void> {
    await fetchAPI(`/templates/${id}/lock`, { method: 'POST' });
}
