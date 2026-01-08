'use client';

import { ToolUsageRecord } from "@/app/api/api";

export default function ToolInspectionModal({ tool, onClose }: { tool: ToolUsageRecord | null, onClose: () => void }) {
    if (!tool) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-8 bg-black/80 backdrop-blur-sm text-body">
            <div className="panel w-full max-w-4xl max-h-full flex flex-col bg-[#09090b] shadow-2xl border-white/5 animate-in zoom-in-95 duration-200">
                <div className="p-6 border-b border-white/5 flex justify-between items-center bg-[#161618]">
                    <div>
                        <h3 className="text-header font-bold text-blue-400 font-mono flex items-center gap-2">
                            <span className="opacity-50">tool:</span> {tool.name}
                        </h3>
                        <p className="font-bold text-zinc-500 mt-1 uppercase tracking-widest">
                            Execution Trace
                        </p>
                    </div>
                    <button 
                        onClick={onClose}
                        className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all"
                    >
                        ✕
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-8">
                    <div className="space-y-4">
                        <h4 className="font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
                            Arguments
                        </h4>
                        <pre className="p-4 rounded-xl bg-black/40 border border-white/5 text-blue-300 whitespace-pre-wrap font-mono leading-relaxed">
                            {JSON.stringify(JSON.parse(tool.args), null, 2)}
                        </pre>
                    </div>

                    <div className="space-y-4">
                        <h4 className="font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
                            <span className={`w-1.5 h-1.5 rounded-full ${tool.status === 'success' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                            Result Output
                        </h4>
                        <pre className={`p-4 rounded-xl border whitespace-pre-wrap font-mono leading-relaxed ${tool.status === 'success' ? 'bg-black/40 border-white/5 text-zinc-300' : 'bg-red-500/5 border-red-500/20 text-red-400'}`}>
                            {tool.output || tool.error || "No output captured."}
                        </pre>
                    </div>
                </div>

                <div className="p-6 border-t border-white/5 flex justify-between items-center bg-[#0c0c0e]">
                    <div className="flex gap-8 text-zinc-500 font-mono font-bold uppercase tracking-tighter">
                        <span>Status: <span className={tool.status === 'success' ? 'text-emerald-400' : 'text-red-400'}>{tool.status}</span></span>
                        <span>Latency: <span className="text-white">{(tool.duration).toFixed(3)}s</span></span>
                    </div>
                    <button onClick={onClose} className="px-6 py-2 rounded-md bg-[#6366f1] hover:bg-[#818cf8] text-white font-bold transition-all">
                        Dismiss
                    </button>
                </div>
            </div>
        </div>
    );
}