'use client';

export default function ValidationModal({ item, onClose }: { item: any, onClose: () => void }) {
    if (!item) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm text-body">
            <div className="panel w-full max-w-4xl max-h-full flex flex-col bg-background shadow-2xl border-border animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-border flex justify-between items-center bg-muted">
                    <div>
                        <span className="font-bold text-blue-500 uppercase tracking-widest block mb-1">{item.type} Validation</span>
                        <h3 className="text-header font-bold text-foreground">{item.description}</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-muted hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-all"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    <div className="flex items-center gap-12">
                        <div className="space-y-1">
                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest">Outcome</h4>
                            <span className={`px-4 py-1.5 rounded-full font-bold uppercase tracking-widest border ${item.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                {item.status}
                            </span>
                        </div>
                        {(() => {
                            let minCoverage = 0;
                            try {
                                const def = JSON.parse(item.definition || '{}');
                                minCoverage = def.min_coverage || 0;
                            } catch (e) { }

                            if (item.coverage > 0 || minCoverage > 0) {
                                return (
                                    <div className="space-y-1">
                                        <h4 className="font-bold text-muted-foreground uppercase tracking-widest">
                                            Coverage {minCoverage > 0 && <span className="text-xs normal-case opacity-70">(min {minCoverage}%)</span>}
                                        </h4>
                                        <span className={`text-3xl font-black ${item.coverage >= (minCoverage || 80) ? 'text-emerald-400' : 'text-red-500'}`}>
                                            {item.coverage.toFixed(1)}%
                                        </span>
                                    </div>
                                );
                            }
                            return null;
                        })()}
                    </div>

                    <div className="space-y-4">
                        {(() => {
                            if (!item.details) return <p className="text-muted-foreground italic">No technical details provided.</p>;

                            const parts = item.details.split('\n\n');
                            const confirmations = parts[0];
                            const rawOutput = parts.slice(1).join('\n\n');

                            return (
                                <>
                                    <div className="space-y-2">
                                        <h4 className="font-bold text-muted-foreground uppercase tracking-widest">Analysis</h4>
                                        <div className="bg-card p-4 rounded border border-border font-mono text-sm space-y-1">
                                            {item.details ? item.details.split('\n').map((line: string, i: number) => (
                                                <div key={i} className={line.startsWith('✓') ? 'text-emerald-400' : line.includes('does not') || line.includes('Expected') ? 'text-red-400' : 'text-foreground'}>
                                                    {line}
                                                </div>
                                            )) : <span className="text-zinc-500 italic">No analysis details.</span>}
                                        </div>
                                    </div>

                                    {item.definition && (
                                        <div className="space-y-2">
                                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Definition</h4>
                                            <pre className="bg-black/40 p-3 rounded border border-white/5 font-mono text-xs text-zinc-400 whitespace-pre-wrap">
                                                {item.definition}
                                            </pre>
                                        </div>
                                    )}

                                    {item.command && (
                                        <div className="space-y-2">
                                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Command Executed</h4>
                                            <div className="bg-black/40 p-3 rounded border border-white/5 font-mono text-xs text-blue-300 whitespace-pre-wrap break-all">
                                                $ {item.command}
                                            </div>
                                        </div>
                                    )}

                                    {item.input && (
                                        <div className="space-y-2">
                                            <div className="flex justify-between items-center">
                                                <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Standard Input</h4>
                                                {(() => {
                                                    try {
                                                        const def = JSON.parse(item.definition || '{}');
                                                        if (def.stdin_delay) {
                                                            return (
                                                                <span className="text-[10px] font-mono bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded border border-blue-500/20">
                                                                    Delay: {def.stdin_delay}
                                                                </span>
                                                            );
                                                        }
                                                    } catch (e) {
                                                        return null;
                                                    }
                                                })()}
                                            </div>
                                            <pre className="bg-black/40 p-3 rounded border border-white/5 font-mono text-xs text-zinc-400 whitespace-pre-wrap">
                                                {item.input}
                                            </pre>
                                        </div>
                                    )}

                                    {item.output !== undefined && (
                                        <div className="space-y-2">
                                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Standard Output</h4>
                                            <pre className="bg-card p-4 rounded-md border border-border font-mono text-foreground text-xs whitespace-pre-wrap leading-relaxed overflow-auto max-h-[300px]">
                                                {item.output || <span className="opacity-30 italic">(No output)</span>}
                                            </pre>
                                        </div>
                                    )}

                                    {item.error !== undefined && (
                                        <div className="space-y-2">
                                            <h4 className="font-bold text-red-400 uppercase tracking-widest text-[10px]">Standard Error</h4>
                                            <pre className="bg-red-950/20 p-4 rounded-md border border-red-500/20 font-mono text-red-200 text-xs whitespace-pre-wrap leading-relaxed overflow-auto max-h-[300px]">
                                                {item.error || <span className="opacity-30 italic">(No error output)</span>}
                                            </pre>
                                        </div>
                                    )}

                                    {/* Fallback for legacy items without separate fields */}
                                    {!item.output && !item.error && rawOutput && (
                                        <div className="space-y-2">
                                            <h4 className="font-bold text-muted-foreground uppercase tracking-widest text-[10px]">Raw Output (Legacy)</h4>
                                            <pre className="bg-card p-6 rounded-md border border-border font-mono text-foreground text-xs whitespace-pre-wrap leading-relaxed overflow-auto max-h-[400px]">
                                                {rawOutput}
                                            </pre>
                                        </div>
                                    )}
                                </>
                            );
                        })()}
                    </div>
                </div>

                <div className="p-6 border-t border-border flex justify-end bg-muted">
                    <button onClick={onClose} className="px-6 py-2 rounded-md bg-primary hover:bg-primary/80 text-primary-foreground font-bold transition-all">
                        CLOSE
                    </button>
                </div>
            </div>
        </div>
    );
}