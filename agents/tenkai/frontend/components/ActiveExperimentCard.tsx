'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ExperimentRecord } from '@/lib/api';

export default function ActiveExperimentCard({ exp, index }: { exp: ExperimentRecord; index: number }) {
    const [loading, setLoading] = useState<string | null>(null);
    const [localStatus, setLocalStatus] = useState(exp.status);

    const handleControl = async (e: React.MouseEvent, action: 'pause' | 'resume' | 'stop') => {
        e.preventDefault(); // Prevent navigating to report
        e.stopPropagation();

        setLoading(action);
        try {
            const res = await fetch('/api/experiments/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ resultsPath: exp.results_path, action }),
            });
            if (res.ok) {
                if (action === 'stop') setLocalStatus('stopped');
                if (action === 'pause') setLocalStatus('paused');
                if (action === 'resume') setLocalStatus('running');
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(null);
        }
    };

    if (localStatus === 'stopped' || localStatus === 'completed') return null;

    return (
        <Link href={`/reports/${exp.id}`} className={`glass p-6 rounded-2xl border transition-all group block ${localStatus === 'running' ? 'border-blue-500/20 hover:border-blue-500/40' : 'border-amber-500/20 hover:border-amber-500/40'}`}>
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h4 className={`font-bold text-base uppercase tracking-tight group-hover:text-blue-400 transition-colors`}>{exp.name || "Active Run"}</h4>
                    <p className="text-xs text-zinc-500 font-mono mt-0.5">Started {new Date(exp.timestamp).toLocaleTimeString()}</p>
                </div>
                <div className="flex gap-2 items-center">
                    <div className={`text-sm font-black uppercase tracking-widest ${localStatus === 'running' ? 'text-blue-500 animate-pulse' : 'text-amber-500'}`}>
                        {localStatus}
                    </div>

                    <div className="flex gap-1">
                        {localStatus === 'running' ? (
                            <button
                                onClick={(e) => handleControl(e, 'pause')}
                                disabled={loading !== null}
                                className="p-1 hover:bg-amber-500/20 rounded transition-colors text-amber-500"
                                title="Pause"
                            >
                                ⏸️
                            </button>
                        ) : (
                            <button
                                onClick={(e) => handleControl(e, 'resume')}
                                disabled={loading !== null}
                                className="p-1 hover:bg-emerald-500/20 rounded transition-colors text-emerald-500"
                                title="Resume"
                            >
                                ▶️
                            </button>
                        )}
                        <button
                            onClick={(e) => handleControl(e, 'stop')}
                            disabled={loading !== null}
                            className="p-1 hover:bg-red-500/20 rounded transition-colors text-red-500"
                            title="Stop"
                        >
                            ⏹️
                        </button>
                    </div>
                </div>
            </div>
            <div className="flex justify-between items-end mb-2">
                <div className="text-xs font-bold text-zinc-500 uppercase tracking-widest leading-none">
                    {exp.progress ? (
                        <span>{exp.progress.completed} / {exp.progress.total} jobs</span>
                    ) : (
                        <span>Initializing...</span>
                    )}
                </div>
                <div className="text-xs font-mono text-blue-500">
                    {exp.progress ? Math.round(exp.progress.percentage) : 0}%
                </div>
            </div>
            <div className="w-full h-1.5 bg-white/5 rounded-full overflow-hidden">
                <div
                    className={`h-full animate-shimmer ${localStatus === 'running' ? 'bg-blue-500' : 'bg-amber-500'} transition-all duration-500`}
                    style={{ width: `${exp.progress ? exp.progress.percentage : 0}%` }}
                ></div>
            </div>
            <div className="mt-2 flex justify-between items-center text-xs uppercase font-bold tracking-widest">
                <span className="text-zinc-600">Click to view live results</span>
                <span className="text-blue-500">Live Report →</span>
            </div>
        </Link>
    );
}
