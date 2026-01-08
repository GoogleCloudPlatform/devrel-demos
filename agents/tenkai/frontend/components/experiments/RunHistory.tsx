'use client';

import { RunResultRecord } from "@/app/api/api";

interface RunHistoryProps {
    runs: RunResultRecord[];
    selectedRunId: number | null;
    onSelectRun: (run: RunResultRecord) => void;
}

export default function RunHistory({ runs, selectedRunId, onSelectRun }: RunHistoryProps) {
    // Group by alternative
    const alternatives = Array.from(new Set(runs.map(r => r.alternative)));

    return (
        <div className="flex flex-col h-full text-body">
            <div className="p-4 border-b border-[#27272a] bg-[#161618]">
                <h3 className="font-bold uppercase tracking-widest text-[#52525b]">Experiment Runs ({runs.length})</h3>
            </div>
            <div className="flex-1 overflow-y-auto">
                {alternatives.map(alt => {
                    const altRuns = runs.filter(r => r.alternative === alt);
                    return (
                        <div key={alt} className="border-b border-[#27272a]">
                            <div className="px-4 py-2 bg-black/20 text-[#71717a] font-bold uppercase tracking-tighter">
                                {alt}
                            </div>
                            <div className="divide-y divide-[#27272a]/50">
                                {altRuns.map(run => (
                                    <button
                                        key={run.id}
                                        onClick={() => onSelectRun(run)}
                                        className={`w-full text-left p-4 hover:bg-white/5 transition-all flex flex-col gap-2 ${selectedRunId === run.id ? 'bg-[#6366f1]/10 border-l-4 border-l-[#6366f1]' : 'border-l-4 border-l-transparent'}`}
                                    >
                                        <div className="flex justify-between items-start">

                                            <span className="font-mono font-bold text-zinc-400">Rep {run.repetition}</span>
                                            <div className="flex flex-col items-end">
                                                <span className={`font-bold uppercase tracking-widest text-xs ${
                                                    run.status?.toUpperCase() === 'RUNNING' || run.status?.toUpperCase() === 'QUEUED' ? 'text-blue-400' :
                                                    run.status?.toUpperCase() === 'COMPLETED' ? 'text-emerald-400' : 'text-red-500'
                                                }`}>
                                                    {run.status}
                                                </span>
                                                {run.reason && (
                                                    <span className={`font-mono font-bold text-[10px] ${
                                                        run.reason.toUpperCase() === 'SUCCESS' ? 'text-emerald-500' : 'text-red-400'
                                                    }`}>
                                                        {run.reason}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex gap-4 items-center opacity-50 font-mono text-sm">
                                            <span>{run.status === 'RUNNING' || run.status === 'QUEUED' ? '---' : `${(run.duration / 1e9).toFixed(1)}s`}</span>
                                            <span>{run.tests_passed}/{run.tests_passed + run.tests_failed} Tests</span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}