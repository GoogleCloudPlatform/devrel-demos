import { NextRequest, NextResponse } from 'next/server';
import { getExperimentSummaries, getRunResults, saveAIAnalysis, getExperimentById } from '@/lib/api';
import { spawn } from 'child_process';

export async function POST(req: NextRequest, props: { params: Promise<{ id: string }> }) {
    const params = await props.params;
    const { id } = params;

    try {
        let summaries = await getExperimentSummaries(id);
        const runs = await getRunResults(id);
        const experiment = await getExperimentById(id);

        if (summaries.length === 0) {
            if (runs.length === 0) {
                return NextResponse.json({ error: 'No data available for this experiment' }, { status: 400 });
            }

            // Fallback: Calculate stats on the fly
            const { calculateStats, zTestProportions, welchTTest } = await import('@/lib/statistics');
            const stats = calculateStats(runs as any);
            const altNames = Object.keys(stats);
            const controlAlt = experiment?.experiment_control || altNames[0];
            const ref = stats[controlAlt];

            summaries = altNames.map(name => {
                const s = stats[name];
                const successSig = zTestProportions(s.successRate / 100, s.count, ref.successRate / 100, ref.count);
                const durationSig = welchTTest(s.durations, ref.durations);

                return {
                    alternative: name,
                    success_rate: s.successRate,
                    success_count: s.successCount,
                    total_runs: s.count,
                    avg_duration: s.avgDuration,
                    avg_tokens: s.avgTokens,
                    avg_lint: s.avgLint,
                    avg_tests_passed: runs.filter(r => r.alternative === name).reduce((acc, r) => acc + (r.tests_passed || 0), 0) / s.count,
                    avg_tests_failed: runs.filter(r => r.alternative === name).reduce((acc, r) => acc + (r.tests_failed || 0), 0) / s.count,
                    p_success: successSig.p,
                    p_duration: durationSig.p,
                    p_tokens: 1, // Placeholder
                    p_tests_failed: 1 // Placeholder
                } as any;
            });
        }

        // Construct the prompt
        let prompt = `Analyze this AI Agent experiment and provide a technical deep-dive (3-4 paragraphs). 
Focus on:
1. Statistical significance (p-values) of the differences between alternatives.
2. Patterns in failures (tests vs lints vs crashes).
3. Recommendation on which configuration is most production-ready.

Data Summary:\n`;

        summaries.forEach(s => {
            prompt += `- Alt: ${s.alternative}\n`;
            prompt += `  Success Rate: ${s.success_rate.toFixed(1)}% (${s.success_count}/${s.total_runs})\n`;
            prompt += `  Avg Duration: ${s.avg_duration.toFixed(2)}s\n`;
            prompt += `  Avg Tokens: ${(s.avg_tokens / 1000).toFixed(1)}k\n`;
            prompt += `  Avg Lint: ${s.avg_lint.toFixed(1)}\n`;
            prompt += `  Avg Tests: ${s.avg_tests_passed.toFixed(1)} Pass, ${s.avg_tests_failed.toFixed(1)} Fail\n`;
            prompt += `  P-Values (vs Control): Success=${s.p_success?.toFixed(4) || 'N/A'}, Duration=${s.p_duration?.toFixed(4) || 'N/A'}\n`;
        });

        const failures = runs.filter(r => !r.is_success).slice(0, 5);
        if (failures.length > 0) {
            prompt += `\nSample Failures:\n`;
            failures.forEach(f => {
                prompt += `- ${f.alternative} | ${f.scenario}: ${f.error || 'Test/Lint Failure'}\n`;
                if (f.validation_report) {
                    try {
                        const report = JSON.parse(f.validation_report);
                        prompt += `  Validation: ${report.items.filter((i: any) => i.status === 'FAIL').map((i: any) => i.description).join(', ')}\n`;
                    } catch (e) { }
                }
            });
        }

        // Call Gemini CLI
        const analysis = await callGemini(prompt);

        // Save to DB
        await saveAIAnalysis(id, analysis);

        return NextResponse.json({ analysis });
    } catch (error: any) {
        console.error('AI Explanation failed:', error);
        return NextResponse.json({ error: error.message }, { status: 500 });
    }
}

function callGemini(prompt: string): Promise<string> {
    const GEMINI_PATH = '/Users/petruzalek/homebrew/Cellar/node/25.2.0/bin/gemini';
    return new Promise((resolve, reject) => {
        const gemini = spawn(GEMINI_PATH, ['-m', 'gemini-2.5-flash', '--output-format', 'text']);
        let output = '';
        let errorOutput = '';

        gemini.on('error', (err: any) => {
            if (err.code === 'ENOENT') {
                reject(new Error(`Gemini CLI not found at ${GEMINI_PATH}. Please ensure it is installed.`));
            } else {
                reject(err);
            }
        });

        gemini.stdout.on('data', (data) => {
            output += data.toString();
        });

        gemini.stderr.on('data', (data) => {
            errorOutput += data.toString();
        });

        gemini.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Gemini process exited with code ${code}: ${errorOutput || 'Unknown error'}`));
                return;
            }

            // Filter out startup logs and cleanup messages
            const lines = output.split('\n');
            const cleanLines = lines.filter(line =>
                !line.includes('[STARTUP]') &&
                !line.includes('Session cleanup disabled') &&
                line.trim() !== ''
            );

            resolve(cleanLines.join('\n').trim());
        });

        gemini.stdin.write(prompt);
        gemini.stdin.end();
    });
}
