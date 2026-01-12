'use client';

import { RunResultRecord } from "@/app/api/api";
import { Card } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

export default function FailureAnalysis({ runs }: { runs: RunResultRecord[] }) {
    const failedRuns = runs.filter(r => {
        const status = r.status?.toUpperCase();
        return !r.is_success && status !== 'RUNNING' && status !== 'QUEUED';
    });

    const alternatives = Array.from(new Set(runs.map(r => r.alternative))).sort();

    // Matrix: Reason -> Alternative -> Count
    const matrix: Record<string, Record<string, number>> = {};
    const reasonTotals: Record<string, number> = {};

    failedRuns.forEach((run) => {
        const detectedReasons: Set<string> = new Set();

        // 1. Strict Backend Reason Mapping
        switch (run.reason) {
            case "FAILED (TIMEOUT)":
                detectedReasons.add("Execution Timeout");
                break;
            case "FAILED (LOOP)":
                detectedReasons.add("Loop Detected");
                break;
            case "FAILED (ERROR)":
                detectedReasons.add("Runtime Error");
                break;
            case "FAILED (VALIDATION)":
                // 2. Parse Validation Report for specific validation failures
                if (run.validation_report) {
                    try {
                        const report = JSON.parse(run.validation_report);

                        // Check Report Items explicitly
                        if (report.items) {
                            report.items.forEach((item: any) => {
                                if (item.status !== "PASS") {
                                    if (item.type === "test") {
                                        // 1. Functional Test Failure
                                        const testsFailedMatch = item.details?.match(/(\d+) tests failed/);
                                        const failedCount = testsFailedMatch ? parseInt(testsFailedMatch[1]) : 0;
                                        if (failedCount > 0) {
                                            detectedReasons.add("Test Failure");
                                        }

                                        // 2. Coverage Failure (Independent check)
                                        if (item.details?.includes("Requirement:")) {
                                            // Try to parse values
                                            const covMatch = item.details.match(/Cov: ([\d.]+)%/);
                                            const reqMatch = item.details.match(/Requirement: >= ([\d.]+)%/);

                                            if (covMatch && reqMatch) {
                                                const covVal = parseFloat(covMatch[1]);
                                                const reqVal = parseFloat(reqMatch[1]);
                                                if (covVal < reqVal) {
                                                    detectedReasons.add("Test Failure (Coverage)");
                                                }
                                            } else {
                                                // Fallback: If requirements exist but parsing failed, and status is FAIL
                                                // If functional tests passed, it must be coverage
                                                if (failedCount === 0) {
                                                    detectedReasons.add("Test Failure (Coverage)");
                                                }
                                            }
                                        }
                                    } else if (item.type === "lint") {
                                        detectedReasons.add("Lint Violation");
                                    } else if (item.type === "command") {
                                        detectedReasons.add("Command Failure");
                                    } else if (item.type === "model") {
                                        detectedReasons.add("Model Validation Failure");
                                    } else {
                                        detectedReasons.add("Generic Validation Failure");
                                    }
                                }
                            });
                        } else {
                            // Fallback if no items but validation failed (should not happen with new backend)
                            detectedReasons.add("Unknown Validation Failure");
                        }
                    } catch (e) {
                        detectedReasons.add("Corrupt Validation Report");
                    }
                } else {
                    detectedReasons.add("Missing Validation Report");
                }
                break;
            default:
                // Handle cases where Reason might be generic or missing (e.g. legacy/aborted runs)
                detectedReasons.add(run.reason || "Unknown Failure");
                break;
        }

        detectedReasons.forEach(reason => {
            if (!matrix[reason]) matrix[reason] = {};
            if (!matrix[reason][run.alternative]) matrix[reason][run.alternative] = 0;
            matrix[reason][run.alternative]++;

            reasonTotals[reason] = (reasonTotals[reason] || 0) + 1;
        });
    });

    const sortedReasons = Object.entries(reasonTotals).sort((a, b) => b[1] - a[1]).map(e => e[0]);

    if (failedRuns.length === 0) return null;

    return (
        <div className="panel overflow-hidden mt-6 pb-0">
            <div className="p-4 border-b border-white/5 bg-white/[0.02]">
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
                                <TableCell className="font-bold text-zinc-300 flex items-center gap-2 px-6">
                                    <span className={`w-2 h-2 rounded-full ${reason.includes("Timeout") ? "bg-amber-500" :
                                        reason.includes("Test") ? "bg-red-500" :
                                            reason.includes("Lint") ? "bg-blue-400" :
                                                "bg-zinc-500"
                                        }`}></span>
                                    {reason}
                                </TableCell>
                                {alternatives.map(alt => {
                                    const count = matrix[reason]?.[alt] || 0;
                                    return (
                                        <TableCell key={alt} className="text-right font-mono text-zinc-400 px-6">
                                            {count > 0 ? <span className="text-red-400 font-bold">{count}</span> : "-"}
                                        </TableCell>
                                    );
                                })}
                                <TableCell className="text-right font-bold text-zinc-200 px-6">
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