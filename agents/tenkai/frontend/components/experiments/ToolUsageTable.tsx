"use client";

import { useEffect, useState } from "react";
import { ToolStatRow } from "@/app/api/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

interface ToolUsageTableProps {
    experimentId: string | number;
    alternatives: string[];
    filter?: string; // Added filter prop
}

export default function ToolUsageTable({ experimentId, alternatives, filter }: ToolUsageTableProps) {
    const [stats, setStats] = useState<ToolStatRow[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!experimentId) return;
        setLoading(true);
        const query = filter ? `?filter=${filter}` : '';
        fetch(`/api/experiments/${experimentId}/tool-stats${query}`)
            .then(res => {
                if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
                return res.json();
            })
            .then(data => {
                if (data && Array.isArray(data)) {
                    setStats(data);
                } else {
                    console.warn("Tool stats data is empty or invalid:", data);
                    setStats([]);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error("Failed to load tool stats", err);
                setStats([]);
                setLoading(false);
            });
    }, [experimentId, filter]);

    if (loading) return <div className="p-4 text-center text-zinc-500 animate-pulse">Loading tool stats...</div>;
    if (!stats || stats.length === 0) return null;

    // Transform to Matrix: Rows = Tools, Cols = Alternatives
    const tools = Array.from(new Set(stats.map(s => s.tool_name))).sort();
    const matrix: Record<string, Record<string, { total: number; failed: number }>> = {};

    stats.forEach(s => {
        if (!matrix[s.tool_name]) matrix[s.tool_name] = {};
        matrix[s.tool_name][s.alternative] = { total: s.total_calls, failed: s.failed_calls };
    });

    return (
        <div className="panel overflow-hidden mt-6">
            <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                <h3 className="font-bold uppercase tracking-widest text-sm">Tool Call Analysis (Accumulated)</h3>
            </div>
            <div className="overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[200px]">Tool Name</TableHead>
                            {alternatives.map(alt => (
                                <TableHead key={alt} className="text-right">{alt}</TableHead>
                            ))}
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {tools.map(tool => (
                            <TableRow key={tool}>
                                <TableCell className="font-mono font-bold text-blue-400">{tool}</TableCell>
                                {alternatives.map(alt => {
                                    const data = matrix[tool]?.[alt];
                                    if (!data) {
                                        return <TableCell key={alt} className="text-right font-mono text-zinc-700">-</TableCell>;
                                    }
                                    return (
                                        <TableCell key={alt} className="text-right font-mono">
                                            {data.total}
                                            {data.failed > 0 && (
                                                <span className="ml-2 text-red-400 font-bold text-xs">
                                                    ({data.failed} failed)
                                                </span>
                                            )}
                                        </TableCell>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}

