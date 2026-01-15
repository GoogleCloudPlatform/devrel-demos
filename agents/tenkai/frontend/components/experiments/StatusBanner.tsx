'use client';

import { Checkpoint } from "@/app/api/api";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import KillExperimentButton from "../KillExperimentButton";
import ProgressBar from "@/components/ui/progress-bar";

export default function StatusBanner({ checkpoint: initialCheckpoint }: { checkpoint: Checkpoint | null }) {
    const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(initialCheckpoint);

    useEffect(() => {
        setCheckpoint(initialCheckpoint);
    }, [initialCheckpoint]);

    if (!checkpoint) {
        return null;
    }

    const isRunning = checkpoint.status.toUpperCase() === 'RUNNING';

    return (
        <div className="px-6 py-4 bg-[#09090b] border-b border-[#27272a] flex items-center justify-between animate-in slide-in-from-top duration-500 text-body">
            <div className="flex items-center gap-6">
                <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${isRunning ? 'bg-[#6366f1] animate-pulse shadow-[0_0_10px_#6366f1]' : 'bg-amber-500'}`}></div>
                    <span className="font-black uppercase tracking-widest text-[#f4f4f5]">{checkpoint.status}</span>
                </div>

                <div className="h-6 w-px bg-[#27272a]"></div>

                <div className="flex items-center gap-4">
                    <div className="w-64">
                        <ProgressBar
                            percentage={checkpoint.percentage}
                            completed={checkpoint.completed_jobs}
                            total={checkpoint.total_jobs}
                            status={checkpoint.status}
                            showLabel={false}
                        />
                    </div>
                    <span className="font-mono font-bold text-white">{checkpoint.percentage.toFixed(1)}%</span>
                </div>

                <div className="h-6 w-px bg-[#27272a]"></div>
                <div className="flex gap-4">
                    <p className="font-bold uppercase tracking-widest text-[#52525b]">
                        Jobs: <span className="text-[#f4f4f5]">{checkpoint.completed_jobs} / {checkpoint.total_jobs}</span>
                    </p>
                </div>
            </div>

            <div className="flex gap-2">
                {/* No controls here - centralized in Header */}
            </div>
        </div>
    );
}
