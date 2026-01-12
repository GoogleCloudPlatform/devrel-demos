"use client";

import { RunResultRecord } from "@/app/api/api";
import { useState } from "react";

interface RunHistoryProps {
    runs: RunResultRecord[];
    selectedRunId: number | null;
    onSelectRun: (run: RunResultRecord) => void;
    onLoadMore: () => void;
    hasMore: boolean;
    loading: boolean;
}

export default function RunHistory({ runs, selectedRunId, onSelectRun, onLoadMore, hasMore, loading }: RunHistoryProps) {
    const [filter, setFilter] = useState("ALL");

    // Group by alternative
    const alternatives = Array.from(new Set(runs.map(r => r.alternative))).sort((a, b) => {
        // "default" or "control" comes first
        const isAControl = a.toLowerCase() === 'default' || a.toLowerCase() === 'control';
        const isBControl = b.toLowerCase() === 'default' || b.toLowerCase() === 'control';
        if (isAControl && !isBControl) return -1;
        if (!isAControl && isBControl) return 1;
        return a.localeCompare(b);
    });

    return (
        <div className="flex flex-col h-full text-body">
            <div className="p-4 border-b border-[#27272a] bg-[#161618] flex flex-col gap-3">
                <div className="flex justify-between items-center">
                    <h3 className="font-bold uppercase tracking-widest text-[#52525b]">Experiment Runs ({runs.length})</h3>
                </div>
                <select
                    className="w-full bg-black/20 border border-white/10 rounded px-2 py-1 text-xs text-zinc-400 focus:outline-none focus:border-blue-500"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                >
                    <option value="ALL">All Runs</option>
                    <option value="SUCCESS">Success Only</option>
                    <option value="FAILED">Failed Only (All Types)</option>
                    <option value="FAILED (VALIDATION)">Validation Failures</option>
                    <option value="FAILED (TIMEOUT)">Timeouts</option>
                    <option value="FAILED (LOOP)">Loop Detection</option>
                    <option value="FAILED (ERROR)">System Errors</option>
                </select>
            </div>
            <div className="flex-1 overflow-y-auto">
                {alternatives.map(alt => {
                    const altRuns = runs
                        .filter(r => r.alternative === alt)
                        .filter(r => {
                            if (filter === "ALL") return true;
                            if (filter === "SUCCESS") return r.is_success;
                            if (filter === "FAILED") return !r.is_success;
                            return r.reason === filter || r.status === filter; // Loose match for exact reasons
                        })
                        .sort((a, b) => a.id - b.id); // Chronological

                    if (altRuns.length === 0) return null;

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

                                            <span className="font-mono font-bold text-zinc-400">Run {run.id} (Rep {run.repetition})</span>
                                            <div className="flex flex-col items-end">
                                                <span className={`font-bold uppercase tracking-widest text-xs ${run.status?.toUpperCase() === 'RUNNING' || run.status?.toUpperCase() === 'QUEUED' ? 'text-blue-400' :
                                                    run.status?.toUpperCase() === 'COMPLETED' ? 'text-emerald-400' : 'text-red-500'
                                                    }`}>
                                                    {run.status}
                                                </span>
                                                {run.reason && (
                                                    <span className={`font-mono font-bold text-[10px] ${run.reason.toUpperCase() === 'SUCCESS' ? 'text-emerald-500' : 'text-red-400'
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
            {hasMore && (
                <div className="p-4 border-t border-[#27272a] bg-[#161618]">
                    <button
                        onClick={onLoadMore}
                        disabled={loading}
                        className="w-full py-2 px-4 bg-[#27272a] hover:bg-[#3f3f46] text-zinc-300 font-bold uppercase tracking-widest text-xs rounded transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Loading...' : 'Load More Results'}
                    </button>
                </div>
            )}
        </div>
    );
}