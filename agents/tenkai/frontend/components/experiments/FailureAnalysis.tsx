'use client';

import { RunResultRecord } from "@/lib/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

export default function FailureAnalysis({ runs, stats }: { runs: RunResultRecord[], stats?: Record<string, any> }) {
    const alternatives = Array.from(new Set([
        ...runs.map(r => r.alternative),
        ...(stats ? Object.keys(stats).filter(k => k !== 'Combined') : [])
    ])).sort();

    // Matrix: Reason -> Alternative -> Count
    const matrix: Record<string, Record<string, number>> = {};
    const reasonTotals: Record<string, number> = {};

    // 1. Try to use backend-calculated stats first
    let hasStats = false;
    if (stats) {
        Object.entries(stats).forEach(([alt, data]) => {
            if (alt === 'Combined') return;
            if (data.failure_reasons && Object.keys(data.failure_reasons).length > 0) {
                hasStats = true;
                Object.entries(data.failure_reasons).forEach(([reason, count]) => {
                    const c = count as number;
                    if (!matrix[reason]) matrix[reason] = {};
                    matrix[reason][alt] = (matrix[reason][alt] || 0) + c;
                    reasonTotals[reason] = (reasonTotals[reason] || 0) + c;
                });
            }
        });
    }

    // 2. Fallback to local calculation if no backend stats
    if (!hasStats) {
        // identifying that stats are missing, but respecting the rule to NOT calculate locally.
        // We can just return null or show an empty state if no stats are available to enforce usage of backend.
        console.warn("FailureAnalysis: No backend stats available for failure analysis.");
    }

    const sortedReasons = Object.entries(reasonTotals).sort((a, b) => b[1] - a[1]).map(e => e[0]);

    if (Object.keys(reasonTotals).length === 0) return null;

    return (
        <div className="panel overflow-hidden mt-6 pb-0">
            <div className="p-4 border-b border-border bg-muted/40">
                <h3 className="font-bold uppercase tracking-widest text-sm text-foreground">Failure Analysis (Run Count)</h3>
            </div>
            <div className="overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[300px] px-6">Failure Reason</TableHead>
                            {alternatives.map(alt => (
                                <TableHead key={alt} className="text-right px-6">{alt}</TableHead>
                            ))}
                            <TableHead className="text-right w-[100px] px-6">Total</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {sortedReasons.map(reason => (
                            <TableRow key={reason}>
                                <TableCell className="font-bold text-muted-foreground flex items-center gap-2 px-6">
                                    <span className={`w-2 h-2 rounded-full ${reason.includes("Timeout") ? "bg-amber-500" :
                                        reason.includes("Test") ? "bg-red-500" :
                                            reason.includes("Lint") ? "bg-blue-400" :
                                                "bg-zinc-500"
                                        }`}></span>
                                    {reason}
                                </TableCell>
                                {alternatives.map(alt => {
                                    const count = matrix[reason]?.[alt] || 0;
                                    const altData = stats?.[alt];
                                    const pValue = altData?.p_failure_reasons?.[reason];

                                    let sigLevel = '';
                                    if (pValue !== undefined && pValue >= 0) {
                                        if (pValue < 0.01) sigLevel = '***';
                                        else if (pValue < 0.05) sigLevel = '**';
                                        else if (pValue < 0.1) sigLevel = '*';
                                    }

                                    return (
                                        <TableCell key={alt} className="text-right font-mono text-muted-foreground/70 px-6">
                                            <div className="flex items-center justify-end gap-1">
                                                {count > 0 ? <span className="text-red-400 font-bold">{count}</span> : "-"}
                                                {sigLevel && <span className="text-primary font-bold text-xs" title={`p=${pValue?.toFixed(4)}`}>{sigLevel}</span>}
                                            </div>
                                        </TableCell>
                                    );
                                })}
                                <TableCell className="text-right font-bold text-foreground px-6">
                                    {reasonTotals[reason]}
                                </TableCell>
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}