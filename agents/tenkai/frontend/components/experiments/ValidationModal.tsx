'use client';

export default function ValidationModal({ item, onClose }: { item: any, onClose: () => void }) {
    if (!item) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm text-body">
            <div className="panel w-full max-w-4xl max-h-full flex flex-col bg-[#09090b] shadow-2xl border-white/5 animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-[#161618]">
                    <div>
                        <span className="font-bold text-blue-500 uppercase tracking-widest block mb-1">{item.type} Validation</span>
                        <h3 className="text-header font-bold text-white">{item.description}</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-8 space-y-8">
                    <div className="flex items-center gap-12">
                        <div className="space-y-1">
                            <h4 className="font-bold text-zinc-500 uppercase tracking-widest">Outcome</h4>
                            <span className={`px-4 py-1.5 rounded-full font-bold uppercase tracking-widest border ${item.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                                {item.status}
                            </span>
                        </div>
                    </div>

                    <div className="space-y-4">
                        <h4 className="font-bold text-zinc-500 uppercase tracking-widest">Output / Details</h4>
                        <pre className="bg-black/50 p-6 rounded-md border border-white/5 font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed overflow-auto max-h-[400px]">
                            {item.details || "No technical details provided."}
                        </pre>
                    </div>
                </div>

                <div className="p-6 border-t border-white/5 flex justify-end bg-[#0c0c0e]">
                    <button onClick={onClose} className="px-6 py-2 rounded-md bg-[#6366f1] hover:bg-[#818cf8] text-white font-bold transition-all">
                        CLOSE
                    </button>
                </div>
            </div>
        </div>
    );
}