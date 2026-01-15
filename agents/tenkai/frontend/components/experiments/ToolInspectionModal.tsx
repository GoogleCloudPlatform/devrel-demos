'use client';

import { ToolUsageRecord } from "@/app/api/api";

export default function ToolInspectionModal({ tool, onClose }: { tool: ToolUsageRecord | null, onClose: () => void }) {
    if (!tool) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm text-body">
            <div className="panel w-full max-w-4xl max-h-full flex flex-col bg-card shadow-2xl border-border animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted/30">
                    <div>
                        <h3 className="text-header font-bold text-primary font-mono flex items-center gap-2">
                            <span className="opacity-50 text-muted-foreground">tool:</span> {tool.name}
                        </h3>
                        <p className="font-bold text-muted-foreground mt-1 uppercase tracking-widest text-[10px]">
                            Execution Trace
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-muted hover:bg-muted-foreground/20 flex items-center justify-center text-muted-foreground hover:text-foreground transition-all"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    <div className="space-y-4">
                        <h4 className="font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2 text-xs">
                            <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>
                            Arguments
                        </h4>
                        <pre className="p-4 rounded-xl bg-background/50 border border-border text-primary whitespace-pre-wrap font-mono leading-relaxed text-sm">
                            {JSON.stringify(JSON.parse(tool.args), null, 2)}
                        </pre>
                    </div>

                    <div className="space-y-4">
                        <h4 className="font-bold text-muted-foreground uppercase tracking-widest flex items-center gap-2 text-xs">
                            <span className={`w-1.5 h-1.5 rounded-full ${tool.status === 'success' ? 'bg-emerald-500' : 'bg-destructive'}`}></span>
                            Result Output
                        </h4>
                        <pre className={`p-4 rounded-xl border whitespace-pre-wrap font-mono leading-relaxed text-sm ${tool.status === 'success' ? 'bg-background/50 border-border text-foreground' : 'bg-destructive/5 border-destructive/20 text-destructive'}`}>
                            {tool.output || tool.error || "No output captured."}
                        </pre>
                    </div>
                </div>

                <div className="p-6 border-t border-border flex justify-between items-center bg-card">
                    <div className="flex gap-8 text-muted-foreground font-mono font-bold uppercase tracking-tighter text-xs">
                        <span>Status: <span className={tool.status === 'success' ? 'text-emerald-500' : 'text-destructive'}>{tool.status}</span></span>
                        <span>Latency: <span className="text-foreground">{(tool.duration).toFixed(3)}s</span></span>
                    </div>
                    <button onClick={onClose} className="px-6 py-2 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground font-bold transition-all">
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    );
}