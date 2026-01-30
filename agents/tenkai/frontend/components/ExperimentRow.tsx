'use client';

import Link from "next/link";
import { ExperimentRecord } from "@/lib/api";

export default function ExperimentRow({ exp }: { exp: ExperimentRecord }) {
    return (
        <tr className="hover:bg-muted/50 transition-colors text-body">
            <td className="px-6 py-4 font-mono opacity-50">{exp.id}</td>
            <td className="px-6 py-4">
                <Link href={`/experiments/view?id=${exp.id}`} className="font-bold text-foreground hover:text-primary transition-colors truncate block max-w-xs">
                    {exp.name || "—"}
                </Link>
                <div className="text-body opacity-50 mt-1 uppercase tracking-wider truncate font-mono">
                    {exp.id}
                </div>
            </td>
            <td className="px-6 py-4 text-body opacity-80 max-w-md truncate">
                {exp.description || "—"}
            </td>
            <td className="px-6 py-4">
                <span className={`inline-flex items-center px-2 py-0.5 rounded-[3px] font-mono font-bold uppercase tracking-wider ${exp.status.toUpperCase() === 'COMPLETED' ? 'bg-success/10 text-success border border-success/20' :
                    exp.status.toUpperCase() === 'ABORTED' ? 'bg-destructive/10 text-destructive dark:text-red-400 border border-destructive/20' :
                        'bg-warning/10 text-warning border border-warning/20'
                    }`}>
                    {exp.status}
                </span>
            </td>
            <td className="px-6 py-4 text-right">
                <span className={`font-mono font-bold ${(exp.success_rate || 0) >= 90 ? 'text-success' : 'text-muted-foreground'}`}>
                    {(exp.success_rate || 0).toFixed(0)}%
                </span>
            </td>
            <td className="px-6 py-4 text-right font-mono opacity-50">
                {(exp.avg_duration || 0).toFixed(1)}s
            </td>
        </tr>
    );
}
