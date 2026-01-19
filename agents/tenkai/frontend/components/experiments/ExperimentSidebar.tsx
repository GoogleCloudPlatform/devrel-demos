"use client";

import Link from "next/link";
import { useState, useEffect } from "react";
import ExperimentLockToggle from "@/components/experiments/ExperimentLockToggle";
import { ChevronLeft, ChevronRight, Save } from "lucide-react";
import { cn } from "@/lib/utils";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { saveExperimentAnnotations } from "@/app/api/api";
import { toast } from "sonner";

function AnnotationEditor({ experimentId, initialAnnotations }: { experimentId: number, initialAnnotations: string }) {
    const [annotations, setAnnotations] = useState(initialAnnotations || "");
    const [isSaving, setIsSaving] = useState(false);

    // Update local state if prop changes (e.g. navigation)
    useEffect(() => {
        setAnnotations(initialAnnotations || "");
    }, [initialAnnotations]);

    const handleSave = async () => {
        setIsSaving(true);
        try {
            await saveExperimentAnnotations(experimentId, annotations);
            toast.success("Annotations Saved", {
                description: "Your notes have been updated.",
            });
        } catch (error) {
            console.error(error);
            toast.error("Error Saving", {
                description: "Failed to save annotations.",
            });
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="space-y-2">
            <Textarea
                placeholder="Add tags, notes, or observations..."
                className="min-h-[150px] font-mono text-xs bg-muted/30 resize-y"
                value={annotations}
                onChange={(e) => setAnnotations(e.target.value)}
                onBlur={handleSave} // Auto-save on blur
            />
            <div className="flex justify-end">
                <Button variant="ghost" size="sm" onClick={handleSave} disabled={isSaving} className="text-xs h-7 gap-1 text-muted-foreground hover:text-primary">
                    <Save className="w-3 h-3" />
                    {isSaving ? "Saving..." : "Save"}
                </Button>
            </div>
        </div>
    );
}

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
                            <span className="text-foreground text-right">{new Date(experiment.timestamp).toISOString().split('T')[0]}</span>

                            <span className="uppercase opacity-50">Control</span>
                            <span className="text-primary text-right font-bold">{experiment.experiment_control || "—"}</span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h3 className="font-bold uppercase tracking-widest opacity-50">Annotations</h3>
                        <AnnotationEditor experimentId={experiment.id} initialAnnotations={experiment.annotations} />
                    </div>
                </div>
            )}
        </aside>
    );
}
