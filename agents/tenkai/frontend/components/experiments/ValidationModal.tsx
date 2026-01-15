'use client';

export default function ValidationModal({ item, onClose }: { item: any, onClose: () => void }) {
    if (!item) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm text-body">
            <div className="panel w-full max-w-4xl max-h-full flex flex-col bg-card shadow-2xl border-border animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted/30">
                    <div>
                        <span className="font-bold text-primary uppercase tracking-widest block mb-1">{item.type} Validation</span>
                        <h3 className="text-header font-bold text-foreground">{item.description}</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-muted hover:bg-muted-foreground/20 flex items-center justify-center text-muted-foreground hover:text-foreground transition-all"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    <div className="flex items-center gap-12">
                        <div className="space-y-1">
                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-xs">Outcome</h4>
                            <span className={`px-4 py-1.5 rounded-full font-bold uppercase tracking-widest border ${item.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' : 'bg-destructive/10 text-destructive border-destructive/20'}`}>
                                {item.status}
                            </span>
                        </div>
                        {item.coverage > 0 && (
                            <div className="space-y-1">
                                <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-xs">Coverage</h4>
                                <span className={`text-3xl font-black ${item.coverage >= 80 ? 'text-emerald-500' : item.coverage >= 50 ? 'text-amber-500' : 'text-red-500'}`}>
                                    {item.coverage.toFixed(1)}%
                                </span>
                            </div>
                        )}
                    </div>

                    <div className="space-y-4">
                        <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-xs">Output / Details</h4>
                        <pre className="bg-background/50 p-6 rounded-md border border-border font-mono text-foreground whitespace-pre-wrap leading-relaxed overflow-auto max-h-[400px]">
                            {item.details || "No technical details provided."}
                        </pre>
                    </div>
                </div>

                <div className="p-6 border-t border-border flex justify-end bg-card">
                    <button onClick={onClose} className="px-6 py-2 rounded-md bg-primary hover:bg-primary/90 text-primary-foreground font-bold transition-all">
                        CLOSE
                    </button>
                </div>
            </div>
        </div>
    );
}