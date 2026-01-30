'use client';
import Link from 'next/link';
import { ExperimentRecord } from '@/lib/api';
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
        <Link href={`/experiments/view?id=${exp.id}`}>
            <Card className="hover:border-primary/30 bg-card/40 cursor-pointer group transition-all duration-300 border-border">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h4 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors tracking-tight">
                            {exp.name}
                        </h4>
                        <p className="text-xs text-muted-foreground font-mono mt-1">Started {new Date(exp.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</p>
                    </div>
                    <div className="flex gap-3 items-center">

                        <div className={`text-xs font-bold uppercase tracking-widest px-2 py-1 rounded ${status === 'running' ? 'bg-primary/10 text-primary' : 'bg-warning/10 text-warning'}`}>
                            {status}
                        </div>
                    </div>
                </div>

                <div className="flex justify-between items-end mb-2">

                    <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                        {exp.progress ? (
                            <span>{exp.progress.completed} / {exp.progress.total} jobs</span>
                        ) : (
                            <span>Initializing...</span>
                        )}
                    </div>
                    <div className="text-sm font-mono font-bold text-primary">
                        {exp.progress ? Math.round(exp.progress.percentage) : 0}%
                    </div>
                </div>

                <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                        className={`h-full relative ${status === 'running' ? 'bg-primary' : 'bg-warning'} transition-all duration-500`}
                        style={{ width: `${exp.progress ? exp.progress.percentage : 0}%` }}
                    >
                        {status === 'running' && <div className="absolute inset-0 bg-white/20 animate-[shimmer_1s_infinite]"></div>}
                    </div>
                </div>

                <div className="mt-4 flex justify-between items-center text-[10px] uppercase font-bold tracking-widest opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <span className="text-muted-foreground">View Details</span>
                    <span className="text-primary">Live Report →</span>
                </div>
            </Card>
        </Link>
    );
}
