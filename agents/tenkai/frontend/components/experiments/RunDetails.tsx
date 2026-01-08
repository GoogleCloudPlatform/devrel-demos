'use client';

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { RunResultRecord, ToolUsageRecord, MessageRecord, TestResultRecord, LintResultRecord } from '@/app/api/api';

interface RunDetailsProps {
    run: RunResultRecord;
    details: {
        tools: ToolUsageRecord[];
        messages: MessageRecord[];
        files: any[];
        tests: TestResultRecord[];
        lints: LintResultRecord[];
    };
    onInspectTool: (tool: ToolUsageRecord) => void;
    onInspectValidation: (item: any) => void;
}

function ToolMessage({ role, content }: { role: string, content: string }) {
    const [isOpen, setIsOpen] = useState(false);
    let data: any = {};
    try {
        data = JSON.parse(content);
    } catch (e) {
        return <p className="text-red-500 text-xs">Failed to parse tool content: {content}</p>;
    }

    const isUse = role === 'tool_use';
    const label = isUse ? `Tool Call: ${data.name}` : `Tool Result: ${data.status}`;
    const color = isUse ? 'text-blue-400' : (data.status === 'success' ? 'text-emerald-400' : 'text-red-400');
    const borderColor = isUse ? 'border-blue-500/20' : (data.status === 'success' ? 'border-emerald-500/20' : 'border-red-500/20');
    const bgColor = isUse ? 'bg-blue-500/10' : (data.status === 'success' ? 'bg-emerald-500/5' : 'bg-red-500/5');

    return (
        <div className={`w-full my-2 border rounded ${borderColor} ${bgColor} overflow-hidden`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full h-8 px-3 flex items-center justify-between text-xs font-bold uppercase tracking-wider hover:bg-white/5 transition-colors text-left"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown size={14} className={color} /> : <ChevronRight size={14} className={color} />}
                    <span className={color}>{label}</span>
                </div>
                <span className="text-[10px] text-zinc-500 font-mono">{isOpen ? 'COLLAPSE' : 'EXPAND'}</span>
            </button>

            {isOpen && (
                <div className="p-3 border-t border-white/5 font-mono text-xs text-zinc-300 break-words whitespace-pre-wrap max-h-[300px] overflow-y-auto">
                    {isUse ? data.args : data.output}
                </div>
            )}
        </div>
    );
}

export default function RunDetails({
    run,
    details,
    onInspectTool,
    onInspectValidation
}: RunDetailsProps) {
    const [selectedFile, setSelectedFile] = useState<any>(details.files?.[0] || null);

    return (
        <div className="space-y-4 animate-in fade-in slide-in-from-right-4 duration-500 text-body">
            {/* Run Header Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="panel p-4">
                    <p className="font-bold text-zinc-500 uppercase tracking-widest mb-1">Tokens</p>
                    <p className="text-header font-bold">{run.total_tokens?.toLocaleString()}</p>
                    <p className="text-[#52525b] mt-1 uppercase font-mono">In_{run.input_tokens} Out_{run.output_tokens}</p>
                </div>
                <div className="panel p-4">
                    <p className="font-bold text-zinc-500 uppercase tracking-widest mb-1">Tools</p>
                    <p className="text-header font-bold">{run.tool_calls_count}</p>
                </div>
                <div className="panel p-4">
                    <p className="font-bold text-zinc-500 uppercase tracking-widest mb-1">Tests</p>
                    <p className="text-header font-bold text-emerald-400">{run.tests_passed}</p>
                    <p className="text-red-500 mt-1 uppercase font-bold">{run.tests_failed} Failures</p>
                </div>
                <div className="panel p-4">
                    <p className="font-bold text-zinc-500 uppercase tracking-widest mb-1">Lint</p>
                    <p className="text-header font-bold text-amber-400">{run.lint_issues}</p>
                </div>
            </div>

            {/* Validation Report */}
            <div className="panel overflow-hidden">
                <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                    <h4 className="font-bold uppercase tracking-widest text-blue-400">Validation Report</h4>
                    <div className="flex gap-4">
                        {run.validation_report ? (() => {
                            try {
                                const report = JSON.parse(run.validation_report);
                                return (
                                    <span className={`font-bold uppercase tracking-widest ${report.overall_success ? 'text-emerald-400' : 'text-red-500'}`}>
                                        {report.overall_success ? 'SUCCESS' : 'FAILURE'}
                                    </span>
                                );
                            } catch (e) {
                                return <span className="text-zinc-500 italic">PARSE ERROR</span>;
                            }
                        })() : (
                            <span className="text-zinc-500 italic">PENDING</span>
                        )}
                    </div>
                </div>
                <div className="overflow-x-auto">
                    {run.validation_report ? (() => {
                        try {
                            const report = JSON.parse(run.validation_report);
                            if (!report.items || report.items.length === 0) {
                                return <p className="p-10 text-center text-zinc-500 italic">No validation items recorded.</p>;
                            }
                            return (
                                <table className="w-full text-left bg-black/20">
                                    <thead>
                                        <tr className="border-b border-white/5 text-zinc-500 uppercase tracking-widest text-xs">
                                            <th className="px-6 py-3 w-[120px]">Type</th>
                                            <th className="px-6 py-3">Description</th>
                                            <th className="px-6 py-3 text-right w-[150px]">Status</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {report.items.map((item: any, i: number) => {
                                            const typeKey = item.type?.toUpperCase() || 'UNKNOWN';
                                            const typeColors: Record<string, string> = {
                                                'TEST': 'text-blue-400',
                                                'LINT': 'text-amber-400',
                                                'COMMAND': 'text-purple-400',
                                                'MODEL': 'text-rose-400',
                                                'UNKNOWN': 'text-zinc-400'
                                            };
                                            const typeColor = typeColors[typeKey] || 'text-zinc-400';

                                            return (
                                                <tr key={i} className="group cursor-pointer hover:bg-white/[0.02] transition-colors" onClick={() => onInspectValidation(item)}>
                                                    <td className={`px-6 py-4 font-mono font-bold uppercase ${typeColor}`}>
                                                        {item.type}
                                                    </td>
                                                    <td className="px-6 py-4">
                                                        <p className="font-bold text-zinc-300 mb-1 group-hover:text-white transition-colors">{item.description}</p>
                                                        {item.details && (
                                                            <p className="text-zinc-600 text-sm truncate max-w-2xl font-mono">{item.details.split('\n')[0]}</p>
                                                        )}
                                                    </td>
                                                    <td className="px-6 py-4 text-right">
                                                        <div className="flex items-center justify-end gap-3">
                                                            <span className={`font-bold uppercase tracking-wider text-xs px-2 py-1 rounded bg-white/5 ${item.status === 'PASS' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                                                {item.status}
                                                            </span>
                                                        </div>
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            );
                        } catch (e) {
                            return <p className="p-10 text-center text-red-400 italic">Failed to parse validation report.</p>;
                        }
                    })() : (
                        <div className="p-10 text-center space-y-2">
                            <p className="text-zinc-500 italic uppercase tracking-widest font-bold">No data available yet</p>
                            <p className="text-xs text-zinc-600">Validation results appear after the run completes.</p>
                        </div>
                    )}
                </div>
            </div>

            {/* Thread View */}
            <div className="panel overflow-hidden">
                <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                    <h4 className="font-bold uppercase tracking-widest">Conversation Thread</h4>
                </div>
                <div className="p-6 space-y-6 max-h-[600px] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-800">
                    {(!details.messages || !Array.isArray(details.messages) || details.messages.length === 0) && (
                        <p className="text-zinc-500 italic text-center py-10">No thread data available for this run.</p>
                    )}
                    {Array.isArray(details.messages) && details.messages.map((msg, i) => {
                        if (msg.role === 'tool_use' || msg.role === 'tool_result') {
                            return <ToolMessage key={i} role={msg.role} content={msg.content} />;
                        }


                        return (
                            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                <span className="font-bold text-zinc-600 uppercase tracking-tighter mb-2 ml-1">{msg.role}</span>
                                <div className={`p-4 rounded-md max-w-[90%] border ${msg.role === 'user' ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-100' : 'bg-[#161618] border-[#27272a] text-[#f4f4f5]'}`}>
                                    <div className="prose prose-invert prose-sm max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/5">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                            {msg.content}
                                        </ReactMarkdown>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Tool Usage */}
            {details.tools && details.tools.length > 0 && (
                <div className="panel overflow-hidden">
                    <div className="p-4 border-b border-white/5 bg-amber-500/5">
                        <h4 className="font-bold uppercase tracking-widest text-amber-500">Tool Executions</h4>
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-left bg-black/20">
                            <thead>
                                <tr className="border-b border-white/5 text-zinc-500 uppercase tracking-widest text-xs">
                                    <th className="px-6 py-3">Tool</th>
                                    <th className="px-6 py-3 text-center">Status</th>
                                    <th className="px-6 py-3 text-right">Duration</th>
                                    <th className="px-6 py-3 text-right">Details</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {details.tools?.map((tool, i) => (
                                    <tr key={i} className="hover:bg-white/[0.02] transition-colors">
                                        <td className="px-6 py-3 font-mono font-bold text-blue-400">{tool.name}</td>
                                        <td className="px-6 py-3 text-center">
                                            <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${tool.status === 'success' ? 'text-emerald-400 bg-emerald-500/10' : 'text-red-400 bg-red-500/10'}`}>
                                                {tool.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3 text-right text-zinc-500 font-mono">{(tool.duration / 1e9).toFixed(3)}s</td>
                                        <td className="px-6 py-3 text-right">
                                            <button onClick={() => onInspectTool(tool)} className="uppercase text-zinc-500 hover:text-white font-bold text-xs tracking-wider transition-colors border border-white/10 hover:border-white/20 px-3 py-1 rounded">Inspect</button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Workspace Snapshot */}

            {details.files && details.files.length > 0 && (

                <div className="panel overflow-hidden">
                    <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                        <h4 className="font-bold uppercase tracking-widest text-emerald-500">Workspace Snapshot</h4>
                        <span className="text-zinc-500 font-mono uppercase italic">Captured from DB</span>
                    </div>
                    <div className="grid grid-cols-12 h-[500px]">
                        <div className="col-span-4 border-r border-white/5 overflow-y-auto bg-black/20">
                            {details.files?.map((file, i) => (
                                <button
                                    key={i}
                                    onClick={() => setSelectedFile(file)}

                                    className={`w-full p-3 text-left font-mono border-b border-white/5 transition-all hover:bg-white/5 ${selectedFile?.id === file.id ? 'bg-emerald-500/10 text-emerald-400 border-l-2 border-l-emerald-500' : 'text-zinc-400'}`}
                                >
                                    {file.path}
                                </button>
                            ))}
                        </div>
                        <div className="col-span-8 overflow-y-auto bg-black/40 p-4">
                            {selectedFile ? (
                                <pre className="font-mono text-zinc-300 whitespace-pre-wrap">{selectedFile.content}</pre>
                            ) : (
                                <p className="text-zinc-600 italic text-center mt-20 uppercase font-bold tracking-tighter">Select a file to view content</p>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Run Errors & Logs */}
            {(run.error || run.stderr) && (
                <div className="panel overflow-hidden">
                    <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                        <h4 className="font-bold uppercase tracking-widest text-zinc-500">Error Logs</h4>
                    </div>
                    <div className="p-6 bg-[#09090b] font-mono space-y-6 max-h-[500px] overflow-y-auto">
                        {run.error && (
                            <div className="space-y-2">
                                <p className="text-red-500 uppercase font-black tracking-widest border-b border-red-500/20 pb-1">Failure Reason</p>
                                <pre className="text-red-400 bg-red-400/5 p-4 rounded border border-red-500/10 whitespace-pre-wrap">{run.error}</pre>
                            </div>
                        )}
                        {run.stderr && (
                            <div className="space-y-2">
                                <pre className="text-red-400/80 whitespace-pre-wrap">{run.stderr}</pre>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}