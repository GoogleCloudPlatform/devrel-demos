'use client';
import Link from 'next/link';
import { ExperimentRecord } from '@/app/api/api';
import { useExperimentControl, ExperimentStatus } from '@/hooks/useExperimentControl';
import { Card } from './ui/card';

export default function ActiveExperimentCard({ exp, index }: { exp: ExperimentRecord; index: number }) {
    const normalizedStatus = (exp.status?.toLowerCase() || 'idle') as ExperimentStatus;
    const { status, loadingAction, handleControl: originalHandleControl } = useExperimentControl(exp.id, normalizedStatus);

    const handleControlClick = async (e: React.MouseEvent, action: 'stop') => {

        e.preventDefault(); // Prevent navigating to report
        e.stopPropagation();
        await originalHandleControl(action);
    };

    if (status === 'ABORTED' || status === 'completed') return null;

    return (
        <Link href={`/experiments/${exp.id}`}>
            <Card className="hover:border-indigo-500/30 bg-slate-900/40 cursor-pointer group transition-all duration-300">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h4 className="font-bold text-lg text-slate-100 group-hover:text-indigo-400 transition-colors tracking-tight">
                        </h4>
                        <p className="text-xs text-slate-500 font-mono mt-1">Started {new Date(exp.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                    <div className="flex gap-3 items-center">

                        <div className={`text-xs font-bold uppercase tracking-widest px-2 py-1 rounded ${status === 'running' ? 'bg-indigo-500/10 text-indigo-400' : 'bg-amber-500/10 text-amber-400'}`}>
                            {status}
                        </div>
                    </div>
                </div>
                
                <div className="flex justify-between items-end mb-2">

                    <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                        {exp.progress ? (
                            <span>{exp.progress.completed} / {exp.progress.total} jobs</span>
                        ) : (
                            <span>Initializing...</span>
                        )}
                    </div>
                    <div className="text-sm font-mono font-bold text-indigo-400">
                        {exp.progress ? Math.round(exp.progress.percentage) : 0}%
                    </div>
                </div>
                
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                        className={`h-full relative ${status === 'running' ? 'bg-indigo-500' : 'bg-amber-500'} transition-all duration-500`}
                        style={{ width: `${exp.progress ? exp.progress.percentage : 0}%` }}
                    >
                        {status === 'running' && <div className="absolute inset-0 bg-white/20 animate-[shimmer_1s_infinite]"></div>}
                    </div>
                </div>
                
                <div className="mt-4 flex justify-between items-center text-[10px] uppercase font-bold tracking-widest opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <span className="text-slate-600">View Details</span>
                    <span className="text-indigo-400">Live Report →</span>
                </div>
            </Card>
        </Link>
    );
}
