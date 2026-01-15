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
            <div className="p-4 border-b border-border bg-muted/30 flex flex-col gap-3">
                <div className="flex justify-between items-center">
                    <h3 className="font-bold uppercase tracking-widest text-muted-foreground">Experiment Runs ({runs.length})</h3>
                </div>
                <select
                    className="w-full bg-background/50 border border-border rounded px-2 py-1 text-xs text-foreground focus:outline-none focus:border-primary"
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                >
                    <option value="ALL" className="bg-background">All Runs</option>
                    <option value="SUCCESS" className="bg-background">Success Only</option>
                    <option value="FAILED" className="bg-background">Failed Only (All Types)</option>
                    <option value="FAILED (VALIDATION)" className="bg-background">Validation Failures</option>
                    <option value="FAILED (TIMEOUT)" className="bg-background">Timeouts</option>
                    <option value="FAILED (LOOP)" className="bg-background">Loop Detection</option>
                    <option value="FAILED (ERROR)" className="bg-background">System Errors</option>
                </select>
            </div>
            <div className="flex-1 overflow-y-auto">
                {alternatives.map(alt => {
                    const altRuns = runs
                        .filter(r => r.alternative === alt)
                        .filter(r => {
                            if (filter === "ALL") return true;
                            if (filter === "SUCCESS") return r.is_success;
                            if (filter === "FAILED") return !r.is_success && r.status !== 'RUNNING' && r.status !== 'QUEUED' && r.status !== 'running' && r.status !== 'queued';
                            return r.reason === filter || r.status === filter; // Loose match for exact reasons
                        })
                        .sort((a, b) => a.id - b.id); // Chronological

                    if (altRuns.length === 0) return null;

                    return (
                        <div key={alt} className="border-b border-border">
                            <div className="px-4 py-2 bg-muted/10 text-muted-foreground font-bold uppercase tracking-tighter text-xs">
                                {alt}
                            </div>
                            <div className="divide-y divide-border/30">
                                {altRuns.map(run => (
                                    <button
                                        key={run.id}
                                        onClick={() => onSelectRun(run)}
                                        className={`w-full text-left p-4 hover:bg-muted/20 transition-all flex flex-col gap-2 ${selectedRunId === run.id ? 'bg-primary/10 border-l-4 border-l-primary' : 'border-l-4 border-l-transparent'}`}
                                    >
                                        <div className="flex justify-between items-start">

                                            <span className="font-mono font-bold text-muted-foreground text-xs">Run {run.id} (Rep {run.repetition})</span>
                                            <div className="flex flex-col items-end">
                                                <span className={`font-bold uppercase tracking-widest text-[10px] ${run.status?.toUpperCase() === 'RUNNING' || run.status?.toUpperCase() === 'QUEUED' ? 'text-blue-500' :
                                                    run.status?.toUpperCase() === 'COMPLETED' ? 'text-emerald-500' : 'text-destructive'
                                                    }`}>
                                                    {run.status}
                                                </span>
                                                {run.reason && (
                                                    <span className={`font-mono font-bold text-[9px] ${run.reason.toUpperCase() === 'SUCCESS' ? 'text-emerald-500' : 'text-destructive/80'
                                                        }`}>
                                                        {run.reason}
                                                    </span>
                                                )}
                                            </div>
                                        </div>

                                        <div className="flex gap-4 items-center opacity-60 font-mono text-xs text-foreground">
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
                <div className="p-4 border-t border-border bg-muted/20">
                    <button
                        onClick={onLoadMore}
                        disabled={loading}
                        className="w-full py-2 px-4 bg-secondary text-secondary-foreground font-bold uppercase tracking-widest text-[10px] rounded transition-colors disabled:opacity-50"
                    >
                        {loading ? 'Loading...' : 'Load More Results'}
                    </button>
                </div>
            )}
        </div>
    );
}