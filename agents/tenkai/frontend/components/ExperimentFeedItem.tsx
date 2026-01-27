import React from 'react';
import Link from 'next/link';
import { ExperimentRecord } from '@/app/api/api';

export default function ExperimentFeedItem({ exp }: { exp: ExperimentRecord }) {
    const statusColor =
        exp.status === 'completed' ? 'bg-success' :
            exp.status === 'running' ? 'bg-primary' :
                'bg-warning';

    return (
        <Link href={`/experiments/${exp.id}`} className="block group">
            <div className="relative pl-8 py-6 border-l-2 border-border hover:border-primary/50 transition-colors">
                {/* Timeline Dot */}
                <div className={`absolute left-[-5px] top-8 w-2.5 h-2.5 rounded-full ${statusColor} ring-4 ring-background group-hover:scale-125 transition-transform duration-300`} />

                <div className="flex justify-between items-start">
                    <div className="space-y-1">
                        <div className="flex items-center gap-3">
                            <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors">
                                {exp.name || `Experiment #${exp.id}`}
                            </h3>
                            <span className="text-[10px] font-mono text-muted-foreground bg-muted px-2 py-0.5 rounded uppercase tracking-wider">
                                {exp.id}
                            </span>
                        </div>
                        <p className="text-sm text-muted-foreground max-w-2xl line-clamp-2">
                            {exp.description || "No description provided."}
                        </p>
                    </div>

                    <div className="text-right space-y-1">
                        <div className="text-2xl font-black text-foreground">
                            {exp.success_rate != null ? exp.success_rate.toFixed(0) : '0'}
                            <span className="text-sm text-muted-foreground font-medium ml-0.5">%</span>
                        </div>
                        <div className="text-xs font-bold text-muted-foreground uppercase tracking-widest">Success Rate</div>
                    </div>
                </div>

                <div className="mt-4 flex items-center gap-6 text-xs font-mono text-muted-foreground">
                    <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full"></span>
                        {new Date(exp.timestamp).toLocaleDateString()}
                    </span>
                    <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full"></span>
                        {exp.total_jobs} Jobs
                    </span>
                    {exp.avg_duration && (
                        <span className="flex items-center gap-2">
                            <span className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full"></span>
                            {exp.avg_duration.toFixed(1)}s avg
                        </span>
                    )}
                </div>
            </div>
        </Link>
    );
}
