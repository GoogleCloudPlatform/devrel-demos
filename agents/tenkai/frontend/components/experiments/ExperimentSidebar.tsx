"use client";

import Link from "next/link";
import { useState } from "react";
import ExperimentLockToggle from "@/components/experiments/ExperimentLockToggle";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

interface ExperimentSidebarProps {
    experiment: any;
}

export default function ExperimentSidebar({ experiment }: ExperimentSidebarProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    return (
        <aside
            className={cn(
                "border-r border-border bg-background flex flex-col h-full transition-all duration-300 relative",
                isCollapsed ? "w-[60px]" : "w-[300px]"
            )}
        >
            {/* Toggle Handle */}
            <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="absolute -right-3 top-20 w-6 h-6 bg-background border border-border rounded-full flex items-center justify-center text-muted-foreground hover:text-primary z-50 shadow-sm"
                title={isCollapsed ? "Expand Metadata" : "Collapse Metadata"}
            >
                {isCollapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
            </button>

            <div className="p-4 border-b border-border">
                <Link href="/experiments" className="text-body hover:text-white flex items-center mb-4 transition-colors font-bold uppercase tracking-wider justify-center md:justify-start">
                    <svg className="w-4 h-4 md:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
                    {!isCollapsed && <span>Back</span>}
                </Link>

                {!isCollapsed ? (
                    <>
                        <h1 className="text-title leading-tight mb-2 truncate" title={experiment.name}>{experiment.name || "Unnamed"}</h1>
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className={`inline-block w-2.5 h-2.5 rounded-full ${experiment.status?.toUpperCase() === 'RUNNING' ? 'bg-primary animate-pulse shadow-[0_0_8px_var(--primary)]' : (experiment.status?.toUpperCase() === 'COMPLETED' ? 'bg-emerald-500' : 'bg-muted')}`}></span>
                                <span className="text-body font-bold uppercase">{experiment.status}</span>
                            </div>
                            <ExperimentLockToggle
                                experimentId={experiment.id}
                                initialLocked={!!experiment.is_locked}
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex flex-col items-center gap-4">
                        <span className={`inline-block w-2.5 h-2.5 rounded-full ${experiment.status?.toUpperCase() === 'RUNNING' ? 'bg-primary animate-pulse' : (experiment.status?.toUpperCase() === 'COMPLETED' ? 'bg-emerald-500' : 'bg-muted')}`} title={experiment.status}></span>
                        <ExperimentLockToggle
                            experimentId={experiment.id}
                            initialLocked={!!experiment.is_locked}
                        />
                    </div>
                )}
            </div>

            {!isCollapsed && (
                <div className="p-4 space-y-8 overflow-y-auto flex-1 text-body">
                    <div>
                        <h3 className="font-bold uppercase tracking-widest mb-2 opacity-50">Description</h3>
                        <p className="leading-relaxed">
                            {experiment.description || "No description provided."}
                        </p>
                    </div>

                    <div className="space-y-4">
                        <h3 className="font-bold uppercase tracking-widest opacity-50">Metadata</h3>
                        <div className="grid grid-cols-2 gap-y-3">
                            <span className="uppercase opacity-50">ID</span>
                            <span className="text-foreground text-right font-mono font-bold">{experiment.id}</span>

                            <span className="uppercase opacity-50">Started</span>
                            <span className="text-foreground text-right">{new Date(experiment.timestamp).toLocaleDateString()}</span>

                            <span className="uppercase opacity-50">Control</span>
                            <span className="text-primary text-right font-bold">{experiment.experiment_control || "—"}</span>
                        </div>
                    </div>
                </div>
            )}
        </aside>
    );
}
