// Basic Run Record matching DB
export interface RunRecord {
    alternative: string;
    is_success: number | boolean;
    duration: number;
    total_tokens: number;
    tool_calls_count?: number; // Added
    lint_issues?: number;
    status?: string;
}

export interface ExperimentStats {
    count: number;
    successCount: number;
    successRate: number;
    avgDuration: number;
    avgTokens: number;
    avgLint: number;
    avgToolCalls: number; // Added
    durations: number[];
    tokens: number[];
    lints: number[];
    toolCalls: number[]; // Added
}

export function calculateStats(runs: RunRecord[]): Record<string, ExperimentStats> {
    const stats: Record<string, ExperimentStats> = {};
    for (const run of runs) {
        // Skip running jobs for statistics
        if (run.status === 'RUNNING') continue;

        if (!stats[run.alternative]) {
            stats[run.alternative] = {
                count: 0,
                successCount: 0,
                durations: [],
                tokens: [],
                lints: [],
                toolCalls: [],
                avgDuration: 0,
                avgTokens: 0,
                avgLint: 0,
                avgToolCalls: 0,
                successRate: 0
            };
        }
        const s = stats[run.alternative];
        s.count++;
        // Handle boolean or number (0/1) for success
        const success = typeof run.is_success === 'boolean' ? run.is_success : run.is_success === 1;

        if (success) s.successCount++;
        if (run.duration) s.durations.push(run.duration / 1e9); // ns to seconds
        if (run.total_tokens) s.tokens.push(run.total_tokens);
        if (run.lint_issues !== undefined) s.lints.push(run.lint_issues);
        if (run.tool_calls_count !== undefined) s.toolCalls.push(run.tool_calls_count);
    }

    for (const alt in stats) {
        const s = stats[alt];
        s.successRate = (s.successCount / s.count) * 100;
        s.avgDuration = s.durations.length ? s.durations.reduce((a, b) => a + b, 0) / s.durations.length : 0;
        s.avgTokens = s.tokens.length ? s.tokens.reduce((a, b) => a + b, 0) / s.tokens.length : 0;
        s.avgLint = s.lints.length ? s.lints.reduce((a, b) => a + b, 0) / s.lints.length : 0;
        s.avgToolCalls = s.toolCalls.length ? s.toolCalls.reduce((a, b) => a + b, 0) / s.toolCalls.length : 0;
    }
    return stats;
}

export function welchTTest(arr1: number[], arr2: number[]) {
    if (!arr1 || !arr2 || arr1.length < 2 || arr2.length < 2) return { p: 1.0 };

    const n1 = arr1.length;
    const n2 = arr2.length;
    const m1 = mean(arr1);
    const m2 = mean(arr2);
    const v1 = variance(arr1, m1);
    const v2 = variance(arr2, m2);

    const se1 = v1 / n1;
    const se2 = v2 / n2;
    const se = Math.sqrt(se1 + se2);

    if (se === 0) return { p: m1 === m2 ? 1.0 : 0.0 };

    const t = Math.abs(m1 - m2) / se;
    const _df = Math.pow(se1 + se2, 2) / (Math.pow(se1, 2) / (n1 - 1) + Math.pow(se2, 2) / (n2 - 1));
    return { p: studentTCDF(t, _df) }; // Simplified p-value
}

export function zTestProportions(p1: number, n1: number, p2: number, n2: number) {
    if (n1 === 0 || n2 === 0) return { p: 1.0 };

    const p = (p1 * n1 + p2 * n2) / (n1 + n2);
    const se = Math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2));

    if (se === 0) return { p: p1 === p2 ? 1.0 : 0.0 };

    const z = Math.abs(p1 - p2) / se;
    return { p: 2 * (1 - normalCDF(z)) };
}

function mean(arr: number[]) {
    return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function variance(arr: number[], m: number) {
    return arr.reduce((a, b) => a + Math.pow(b - m, 2), 0) / (arr.length - 1);
}

function normalCDF(x: number) {
    const t = 1 / (1 + .2316419 * Math.abs(x));
    const d = .3989423 * Math.exp(-x * x / 2);
    let prob = d * t * (.3193815 + t * (-.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))));
    if (x > 0) prob = 1 - prob;
    return prob;
}

function studentTCDF(t: number, df: number) {
    // Approximation for high DF using normal CDF
    return 2 * (1 - normalCDF(t));
}

interface SigTestResult {
    p: number;
    level?: string;
}

interface SigTestComparison {
    successRate: SigTestResult;
    avgDuration: SigTestResult;
    avgTokens: SigTestResult;
    avgToolCalls: SigTestResult; // Added
}

export function calculateSigTests(runs: RunRecord[], referenceAlt: string) {
    const stats = calculateStats(runs);
    const ref = stats[referenceAlt];
    if (!ref) return {};

    const results: Record<string, SigTestComparison> = {};
    for (const alt in stats) {
        if (alt === referenceAlt) continue;
        const s = stats[alt];

        results[alt] = {
            successRate: zTestProportions(s.successCount / s.count, s.count, ref.successCount / ref.count, ref.count),
            avgDuration: welchTTest(s.durations, ref.durations),
            avgTokens: welchTTest(s.tokens, ref.tokens),
            avgToolCalls: welchTTest(s.toolCalls, ref.toolCalls) // Added
        };

        // Format markers
        const metrics: (keyof SigTestComparison)[] = ['successRate', 'avgDuration', 'avgTokens', 'avgToolCalls'];
        for (const metric of metrics) {
            const p = results[alt][metric].p;
            results[alt][metric].level = p < 0.01 ? '***' : p < 0.05 ? '**' : p < 0.1 ? '*' : '';
        }
    }
    return results;
}
