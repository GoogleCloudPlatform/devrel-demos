'use client';

import { useRouter } from 'next/navigation';
import { ExperimentRecord } from '@/lib/api';

export default function ExperimentRow({ exp }: { exp: ExperimentRecord }) {
    const router = useRouter();

    return (
        <tr
            onClick={() => router.push(`/reports/${exp.id}`)}
            className="group hover:bg-white/[0.04] transition-all cursor-pointer border-b border-white/5 last:border-0 relative"
        >
            <td className="px-6 py-5 w-[200px] max-w-[200px]">
                <div className="font-semibold text-base text-gray-200 group-hover:text-[#4285F4] transition-colors tracking-tight truncate" title={exp.name}>
                    {exp.name || "Unnamed"}
                </div>
                <div className="text-xs font-mono text-zinc-500 mt-0.5 uppercase tracking-wider truncate">
                    {new Date(exp.timestamp).toLocaleDateString()}
                </div>
            </td>

            <td className="px-6 py-5">
                <div className="text-base text-zinc-300 line-clamp-2 leading-relaxed" title={exp.description}>
                    {exp.description || <span className="text-zinc-600 italic text-sm">No description provided</span>}
                </div>
            </td>

            <td className="px-6 py-5 whitespace-nowrap font-mono text-base text-gray-300">
                {exp.duration_total != null ? (exp.duration_total / 1e9).toFixed(2) + 's' : '—'}
            </td>

            <td className="px-6 py-5 whitespace-nowrap">
                <span className={`text-base font-mono font-bold ${!exp.success_rate || exp.success_rate === 'N/A' ? 'text-zinc-600' :
                    parseFloat(exp.success_rate) >= 90 ? 'text-[#34A853]' :
                        parseFloat(exp.success_rate) >= 70 ? 'text-[#FBBC05]' :
                            'text-[#EA4335]'
                    }`}>
                    {exp.success_rate || '—'}
                </span>
            </td>

            <td className="px-6 py-5 text-right whitespace-nowrap w-[100px]">
                <div className="flex items-center justify-end gap-3">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-widest border ${exp.status === 'completed' ? 'bg-[#34A853]/10 text-[#34A853] border-[#34A853]/20' :
                        exp.status === 'running' ? 'bg-[#4285F4]/10 text-[#4285F4] border-[#4285F4]/20 animate-pulse' :
                            'bg-[#FBBC05]/10 text-[#FBBC05] border-[#FBBC05]/20'
                        }`}>
                        {exp.status === 'running' && <span className="w-1.5 h-1.5 rounded-full bg-current mr-2 animate-ping" />}
                        {exp.status}
                    </span>
                    <button
                        onClick={async (e) => {
                            e.stopPropagation();
                            if (!window.confirm(`Are you sure you want to delete "${exp.name}"?`)) return;
                            try {
                                const res = await fetch(`/api/experiments/${exp.id}`, { method: 'DELETE' });
                                if (res.ok) {
                                    router.refresh();
                                } else {
                                    alert("Failed to delete experiment");
                                }
                            } catch (e) {
                                alert("Error deleting experiment");
                            }
                        }}
                        className="p-1.5 text-zinc-600 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors"
                        title="Delete Experiment"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4">
                            <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.52.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
                        </svg>
                    </button>
                </div>
            </td>
        </tr>
    );
}
