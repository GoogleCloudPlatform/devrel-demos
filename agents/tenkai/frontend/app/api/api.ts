/* eslint-disable @typescript-eslint/no-explicit-any */
import {
    ExperimentRecord,
    Checkpoint,
    ExperimentSummaryRow as ExperimentSummaryRecord,
    RunResult,
    ConfigBlock
} from '@/types/domain';

export type { ExperimentRecord, ExperimentSummaryRecord, Checkpoint };

const API_BASE = typeof window === 'undefined'
    ? 'http://127.0.0.1:8080/api'
    : '/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    const res = await fetch(url, {
        cache: 'no-store', // Always fetch fresh data
        ...options
    });

    if (!res.ok) {
        // Handle 404 gracefully for some resources if needed, or throw
        if (res.status === 404) return null as any;
        throw new Error(`API call failed: ${res.status} ${res.statusText} at ${url}`);
    }

    return res.json();
}

export type RunResultRecord = RunResult;

export interface ToolUsageRecord {
    id: number;
    run_id: number;
    name: string;
    args: string;
    status: string;
    output: string;
    error: string;
    duration: number; // seconds
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
export interface JobResponse {
    job_id?: string;
    error?: string;
}

export async function getExperiments(): Promise<ExperimentRecord[]> {
    try {
        return (await fetchAPI<ExperimentRecord[]>('/experiments')) || [];
    } catch (e) {
        console.error("Failed to fetch experiments:", e);
        return [];
    }
}

export async function getExperimentById(id: number | string): Promise<ExperimentRecord | null> {
    return fetchAPI<ExperimentRecord>(`/experiments/${id}`);
}

export async function getGlobalStats() {
    const data = await fetchAPI<any>('/stats');
    if (!data) return { totalRuns: 0, avgSuccessRate: '0%' };
    return {
        totalRuns: data.total_runs || 0,
        avgSuccessRate: (data.avg_success_rate || 0).toFixed(1) + '%'
    };
}

export async function getReportContent(reportPath: string): Promise<string> {
    return ""; // Deprecated
}

export async function getCheckpoint(idOrPath: string): Promise<Checkpoint | null> {
    // Determine ID from input (could be "experiments/123" or "123")
    const id = idOrPath.toString().split('/').pop();
    if (!id) return null;

    const exp = await getExperimentById(id);
    if (!exp) return null;

    return {
        experiment_id: exp.id,
        status: exp.status,
        total_jobs: exp.progress?.total || exp.total_jobs || 0,
        completed_jobs: exp.progress?.completed || exp.completed_jobs || 0,
        percentage: exp.progress?.percentage || 0,
        last_update: new Date().toISOString()
    };
}

// Fetch a single experiment by ID (Alias)
export function getExperiment(id: number): Promise<ExperimentRecord | null> {
    return getExperimentById(id);
}

export async function saveAIAnalysis(id: number | string, analysis: string) {
    return fetchAPI(`/experiments/${id}/analysis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ analysis })
    });
}

export async function saveExperimentAnnotations(id: number | string, annotations: string) {
    const res = await fetchAPI(`/experiments/${id}/annotations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ annotations })
    });
    if (!res) throw new Error("Failed to save annotations: Endpoint not found");
    return res;
}

export async function getSimplifiedMetrics(id: number | string) {
    // Derived from getExperiment
    const exp = await getExperimentById(id);
    if (!exp) return null;

    return {
        total: exp.total_jobs || 0,
        successful: exp.successful_runs || 0,
        successRate: (exp.success_rate || 0).toFixed(1) + '%',
        avgDuration: (exp.avg_duration || 0).toFixed(1) + 's',
        avgTokens: ((exp.avg_tokens || 0) / 1000).toFixed(1) + 'k',
        totalLint: exp.total_lint || 0,
        results: []
    };
}

export async function getExperimentSummaries(id: number | string, filter?: string): Promise<ExperimentSummaryRecord[]> {
    const query = filter ? `?filter=${filter}` : '';
    return fetchAPI<ExperimentSummaryRecord[]>(`/experiments/${id}/summaries${query}`);
}

export async function getRunResults(experimentId: string | number, page: number = 1, limit: number = 1000): Promise<RunResultRecord[]> {
    return (await fetchAPI<RunResultRecord[]>(`/experiments/${experimentId}/runs?page=${page}&limit=${limit}`)) || [];
}
export async function getToolUsage(runId: number): Promise<ToolUsageRecord[]> {
    const res = await fetchAPI<ToolUsageRecord[]>(`/runs/${runId}/tools`);
    if (!res) return [];
    return res.map(r => ({
        ...r,
        duration: (r.duration || 0) / 1e9 // Convert nanoseconds to seconds for UI
    }));
}

export async function getMessages(runId: number, page = 1, limit = 1000): Promise<MessageRecord[]> {
    return (await fetchAPI<MessageRecord[]>(`/runs/${runId}/messages?page=${page}&limit=${limit}`)) || [];
}

export async function getRunFiles(runId: number) {
    return (await fetchAPI<any[]>(`/runs/${runId}/files`)) || [];
}

export async function getTestResults(runId: number): Promise<TestResultRecord[]> {
    return (await fetchAPI<TestResultRecord[]>(`/runs/${runId}/tests`)) || [];
}

export async function getLintResults(runId: number): Promise<LintResultRecord[]> {
    return (await fetchAPI<LintResultRecord[]>(`/runs/${runId}/lint`)) || [];
}


export async function getNextExperimentNumber(nameBase: string): Promise<number> {
    return 0; // Not needed if Go handles ID/Naming
}

export async function getConfigFile(experimentId: number | string, relativePath: string): Promise<string | null> {
    return null; // File access restricted
}
// Fetch all scenarios from API
export async function getScenarios(): Promise<any[]> {
    try {
        return (await fetchAPI<any[]>('/scenarios')) || [];
    } catch (e) {
        console.error("Failed to fetch scenarios:", e);
        return [];
    }
}

export async function getScenarioById(id: string): Promise<any | null> {
    // Implement detail endpoint or filter list
    const scenarios = await getScenarios();
    return scenarios.find(s => s.id === id) || null;
}

export async function getTemplates(): Promise<any[]> {
    try {
        return (await fetchAPI<any[]>('/templates')) || [];
    } catch (e) {
        console.error("Failed to fetch templates:", e);
        return [];
    }
}


export async function getTemplateConfig(name: string): Promise<any | null> {
    // Templates endpoint should probably return details?
    // Current list endpoint returns basic info.
    // Assuming backend might need /api/templates/{id} for content.
    return null;
}

export interface ToolStatRow {
    alternative: string;
    tool_name: string;
    total_calls: number;
    failed_calls: number; // Added
    avg_calls: number;
}

export async function getToolStats(experimentId: number, filter?: string): Promise<ToolStatRow[]> {
    const query = filter ? `?filter=${filter}` : '';
    return fetchAPI<ToolStatRow[]>(`/experiments/${experimentId}/tool-stats${query}`);
}

export async function reValidateRun(runId: number): Promise<JobResponse> {
    return fetchAPI<JobResponse>(`/runs/${runId}/reval`, {
        method: 'POST'
    });
}

export async function reValidateExperiment(experimentId: number): Promise<JobResponse> {
    return fetchAPI<JobResponse>(`/experiments/${experimentId}/reval`, {
        method: 'POST'
    });
}

export async function toggleLock(experimentId: number, locked: boolean): Promise<any> {
    return fetchAPI(`/experiments/${experimentId}/lock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locked }),
    });
}

export async function toggleScenarioLock(scenarioId: string, locked: boolean): Promise<any> {
    return fetchAPI(`/scenarios/${scenarioId}/lock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locked }),
    });
}

export async function toggleTemplateLock(templateId: string, locked: boolean): Promise<any> {
    return fetchAPI(`/templates/${templateId}/lock`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locked }),
    });
}
export async function getBlocks(): Promise<ConfigBlock[]> {
    try {
        return (await fetchAPI<ConfigBlock[]>('/blocks')) || [];
    } catch (e) {
        console.error("Failed to fetch blocks:", e);
        return [];
    }
}
