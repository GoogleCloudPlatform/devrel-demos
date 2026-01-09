'use client';

import Link from "next/link";
import { ExperimentRecord } from "@/app/api/api";

export default function ExperimentRow({ exp }: { exp: ExperimentRecord }) {
    return (
        <tr className="hover:bg-white/[0.02] transition-colors text-body">
            <td className="px-6 py-4 font-mono opacity-50">{exp.id}</td>
            <td className="px-6 py-4">
                <Link href={`/experiments/${exp.id}`} className="font-bold text-[#f4f4f5] hover:text-[#6366f1] transition-colors truncate block max-w-xs">
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
                <span className={`inline-flex items-center px-2 py-0.5 rounded-[3px] font-mono font-bold uppercase tracking-wider ${
                    exp.status.toUpperCase() === 'COMPLETED' ? 'bg-green-950/30 text-green-400 border border-green-900/50' :
                    exp.status.toUpperCase() === 'ABORTED' ? 'bg-red-950/30 text-red-400 border border-red-900/50' :
                    'bg-yellow-950/30 text-yellow-400 border border-yellow-900/50'
                }`}>
                    {exp.status}
                </span>
            </td>
            <td className="px-6 py-4 text-right">
                <span className={`font-mono font-bold ${(exp.success_rate || 0) >= 90 ? 'text-green-500' : 'text-zinc-500'}`}>
                    {(exp.success_rate || 0).toFixed(0)}%
                </span>
            </td>
            <td className="px-6 py-4 text-right font-mono opacity-50">
                {(exp.avg_duration || 0).toFixed(1)}s
            </td>
        </tr>
    );
}
