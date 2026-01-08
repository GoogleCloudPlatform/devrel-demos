'use client';

import { RunResultRecord } from "@/app/api/api";
import { Card } from "@/components/ui/card";

export default function FailureAnalysis({ runs }: { runs: RunResultRecord[] }) {
    const failedRuns = runs.filter(r => {
        const status = r.status?.toUpperCase();
        return !r.is_success && status !== 'RUNNING' && status !== 'QUEUED' && status !== 'PAUSED';
    });

    // Group by common error patterns
    const errorPatterns: Record<string, { count: number, alternatives: string[] }> = {};

    failedRuns.forEach(run => {
        let reason = "Unknown failure";
        if (run.error) {
            if (run.error.includes("timeout")) reason = "Execution Timeout";
            else if (run.error.includes("token")) reason = "Context Overflow";
            else if (run.error.includes("compile")) reason = "Compilation Error";
            else reason = run.error.split('\n')[0].substring(0, 60);
        } else if (run.tests_failed > 0) {
            reason = "Test Regression";
        } else if (run.lint_issues > 0) {
            reason = "Style/Lint Violation";
        }

        if (!errorPatterns[reason]) errorPatterns[reason] = { count: 0, alternatives: [] };
        errorPatterns[reason].count++;
        if (!errorPatterns[reason].alternatives.includes(run.alternative)) {
            errorPatterns[reason].alternatives.push(run.alternative);
        }
    });

    const patterns = Object.entries(errorPatterns).sort((a, b) => b[1].count - a[1].count);

    return (
        <Card title="Failure Patterns Analysis" className="text-body">
            <div className="space-y-6">
                {patterns.length === 0 ? (
                    <p className="text-zinc-500 italic py-4">No critical failure patterns detected.</p>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-4">
                            <h4 className="font-bold uppercase tracking-widest text-[#52525b] mb-4 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                                Top Critical Failures
                            </h4>
                            <div className="space-y-3">
                                {patterns.slice(0, 5).map(([reason, data], i) => (
                                    <div key={i} className="panel p-3 bg-red-500/[0.02] border-red-500/10 flex flex-col gap-2 group hover:bg-red-500/5 transition-colors">
                                        <div className="flex justify-between items-start">
                                            <span className="font-bold text-zinc-300">{reason}</span>
                                            <span className="font-black text-red-500 bg-red-500/10 px-2 py-0.5 rounded uppercase">{data.count} runs</span>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {data.alternatives.map(alt => (
                                                <span key={alt} className="text-zinc-500 px-1.5 py-0.5 bg-white/5 rounded font-mono">{alt}</span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h4 className="font-bold uppercase tracking-widest text-[#52525b] mb-4 flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                Common Regressions
                            </h4>
                            <div className="space-y-3">
                                {patterns.slice(5, 10).map(([reason, data], i) => (
                                    <div key={i} className="panel p-3 bg-amber-500/[0.02] border-amber-500/10 flex flex-col gap-2 group hover:bg-amber-500/5 transition-colors">
                                        <div className="flex justify-between items-start">
                                            <span className="font-bold text-amber-500/80">{reason}</span>
                                            <span className="font-black text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded uppercase">{data.count} runs</span>
                                        </div>
                                        <div className="flex flex-wrap gap-2">
                                            {data.alternatives.map(alt => (
                                                <span key={alt} className="text-zinc-500 px-1.5 py-0.5 bg-white/5 rounded font-mono">{alt}</span>
                                            ))}
                                        </div>
                                    </div>
                                ))}
                                {patterns.length <= 5 && (
                                    <div className="py-8 text-center text-zinc-600 opacity-50 italic">
                                        No secondary regressions identified.
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </Card>
    );
}