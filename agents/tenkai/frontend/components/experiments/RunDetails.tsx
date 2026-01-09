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
function CollapsibleEvent({
    title,
    timestamp,
    color = "text-zinc-400",
    bgColor = "bg-zinc-500/10",
    borderColor = "border-zinc-500/20",
    children,
    defaultOpen = false
}: {
    title: React.ReactNode;
    timestamp?: string;
    color?: string;
    bgColor?: string;
    borderColor?: string;
    children: React.ReactNode;
    defaultOpen?: boolean;
}) {
    const [isOpen, setIsOpen] = useState(defaultOpen);

    return (
        <div className={`w-full my-2 border rounded ${borderColor} ${bgColor} overflow-hidden`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full h-8 px-3 flex items-center justify-between text-xs font-bold uppercase tracking-wider hover:bg-white/5 transition-colors text-left"
            >
                <div className="flex items-center gap-2">
                    {isOpen ? <ChevronDown size={14} className={color} /> : <ChevronRight size={14} className={color} />}
                    <span className={color}>{title}</span>
                </div>
                <div className="flex items-center gap-3">
                    {timestamp && <span className="text-[10px] text-zinc-500 font-mono">{new Date(timestamp).toLocaleTimeString()}</span>}
                    <span className="text-[10px] text-zinc-600 font-mono opacity-50">{isOpen ? 'COLLAPSE' : 'EXPAND'}</span>
                </div>
            </button>

            {isOpen && (
                <div className="p-3 border-t border-white/5 font-mono text-xs text-zinc-300 break-words max-h-[500px] overflow-y-auto bg-black/20">
                    {children}
                </div>
            )}
        </div>
    );
}

function JsonView({ data }: { data: any }) {
    if (typeof data === 'string') {
        try {
            const parsed = JSON.parse(data);
            if (parsed && typeof parsed === 'object') {
                return <pre className="whitespace-pre-wrap">{JSON.stringify(parsed, null, 2)}</pre>;
            }
        } catch (e) {}
        return <div className="whitespace-pre-wrap">{data}</div>;
    }
    return <pre className="whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>;
}

function InitEvent({ timestamp }: { timestamp: string }) {
    return (
        <div className="w-full my-4 flex items-center justify-center">
            <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-1 rounded-full text-xs font-mono font-bold uppercase tracking-widest">
                🚀 Session Started at {new Date(timestamp).toLocaleTimeString()}
            </div>
        </div>
    );
}

function ErrorEvent({ content, timestamp }: { content: string, timestamp: string }) {
    let data: any = { message: content };
    try {
        data = JSON.parse(content);
    } catch {}

    const severity = data.severity || "error";
    const color = severity === "warning" ? "text-amber-400" : "text-red-400";
    const borderColor = severity === "warning" ? "border-amber-500/20" : "border-red-500/20";
    const bgColor = severity === "warning" ? "bg-amber-500/5" : "bg-red-500/5";

    return (
        <CollapsibleEvent
            title={<span className="flex items-center gap-2">⚠️ {data.type?.toUpperCase() || "ERROR"}: {severity}</span>}
            timestamp={timestamp}
            color={color}
            borderColor={borderColor}
            bgColor={bgColor}
            defaultOpen={true}
        >
            <JsonView data={data.message || content} />
        </CollapsibleEvent>
    );
}

function ResultEvent({ content, timestamp }: { content: string, timestamp: string }) {
    let data: any = {};
    try {
        data = JSON.parse(content);
    } catch {
        return <GenericEvent role="result" content={content} timestamp={timestamp} />;
    }

    return (
        <CollapsibleEvent
            title={`🏁 Execution Result: ${data.status}`}
            timestamp={timestamp}
            color="text-indigo-400"
            borderColor="border-indigo-500/20"
            bgColor="bg-indigo-500/10"
            defaultOpen={true}
        >
            <div className="space-y-4">
                {data.stats && (
                    <div className="grid grid-cols-3 gap-2 text-center">
                        <div className="bg-black/40 p-2 rounded border border-white/5">
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">Tokens</div>
                            <div className="text-white font-mono text-sm font-bold">{data.stats.total_tokens?.toLocaleString()}</div>
                        </div>
                        <div className="bg-black/40 p-2 rounded border border-white/5">
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">Input</div>
                            <div className="text-zinc-400 font-mono text-sm">{data.stats.input_tokens?.toLocaleString()}</div>
                        </div>
                        <div className="bg-black/40 p-2 rounded border border-white/5">
                            <div className="text-[10px] text-zinc-500 uppercase font-bold">Output</div>
                            <div className="text-zinc-400 font-mono text-sm">{data.stats.output_tokens?.toLocaleString()}</div>
                        </div>
                    </div>
                )}
            </div>
        </CollapsibleEvent>
    );
}

function GenericEvent({ role, content, timestamp }: { role: string, content: string, timestamp: string }) {
    return (
        <CollapsibleEvent
            title={`Event: ${role}`}
            timestamp={timestamp}
            color="text-zinc-500"
            bgColor="bg-zinc-900/50"
            borderColor="border-zinc-800"
        >
            <JsonView data={content} />
        </CollapsibleEvent>
    );
}

function ToolMessage({ role, content, timestamp }: { role: string, content: string, timestamp: string }) {
    let data: any = {};
    try {
        data = JSON.parse(content);
    } catch (e) {
        return <p className="text-red-500 text-xs">Failed to parse tool content: {content}</p>;
    }

    const isUse = role === 'tool_use';
    const label = isUse ? `Tool Call: ${data.name}` : `Tool Result`;
    const statusLabel = !isUse ? `(${data.status})` : "";
    
    const color = isUse ? 'text-blue-400' : (data.status === 'success' ? 'text-emerald-400' : 'text-red-400');
    const borderColor = isUse ? 'border-blue-500/20' : (data.status === 'success' ? 'border-emerald-500/20' : 'border-red-500/20');
    const bgColor = isUse ? 'bg-blue-500/10' : (data.status === 'success' ? 'bg-emerald-500/5' : 'bg-red-500/5');
    return (
        <CollapsibleEvent
            title={<span>{label} <span className="opacity-50">{statusLabel}</span></span>}
            timestamp={timestamp}
            color={color}
            borderColor={borderColor}
            bgColor={bgColor}
        >
            <JsonView data={isUse ? data.args : (data.error || data.output)} />
        </CollapsibleEvent>
    );
}

function RunStatusBanner({ run }: { run: RunResultRecord }) {
    let statusColor = "bg-zinc-800 text-zinc-400 border-zinc-700";
    let icon = "⏳";
    let statusText = run.status || "UNKNOWN";
    let reasonText = "";

    if (run.status === 'COMPLETED' || run.status === 'completed') {
        if (run.is_success) {
            statusColor = "bg-emerald-500/20 border-emerald-500/30 text-emerald-400";
            icon = "✅";
            statusText = "SUCCESS";
        } else {
            statusColor = "bg-red-500/20 border-red-500/30 text-red-400";
            icon = "❌";
            statusText = "FAILED";
            reasonText = run.reason || "Unknown Failure";
        }
    } else if (run.status === 'ABORTED' || run.status === 'aborted') {
        statusColor = "bg-zinc-700/50 border-zinc-600 text-zinc-300";
        icon = "🛑";
        statusText = "ABORTED";
    }

    return (
        <div className={`p-4 border rounded-md mb-6 flex items-center justify-between ${statusColor}`}>
            <div className="flex items-center gap-3">
                <span className="text-2xl">{icon}</span>
                <div>
                    <h3 className="font-black uppercase tracking-widest text-lg leading-none">{statusText}</h3>
                    {reasonText && <p className="text-xs font-mono opacity-80 mt-1 uppercase">{reasonText}</p>}
                </div>
            </div>
            <div className="text-right">
                <p className="text-xs font-bold uppercase tracking-widest opacity-60">Run ID</p>
                <p className="font-mono font-bold text-lg leading-none">{run.id}</p>
            </div>
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
            <RunStatusBanner run={run} />
            
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
                        // 1. Tool Events
                        if (msg.role === 'tool_use' || msg.role === 'tool_result') {
                            return <ToolMessage key={i} role={msg.role} content={msg.content} timestamp={msg.timestamp} />;
                        }
                        // 2. Special System Events
                        if (msg.role === 'init') {
                            return <InitEvent key={i} timestamp={msg.timestamp} />;
                        }
                        if (msg.role === 'result') {
                            return <ResultEvent key={i} content={msg.content} timestamp={msg.timestamp} />;
                        }
                        if (msg.role === 'error') {
                            return <ErrorEvent key={i} content={msg.content} timestamp={msg.timestamp} />;
                        }


                        // 3. Chat Messages (User/Model/Assistant)
                        if (msg.role === 'user' || msg.role === 'model' || msg.role === 'assistant') {
                            const isUser = msg.role === 'user';
                            return (
                                <div key={i} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} my-4`}>
                                    <span className="font-bold text-zinc-600 uppercase tracking-tighter mb-2 ml-1 text-xs">{msg.role}</span>
                                    <div className={`p-4 rounded-md max-w-[90%] border shadow-sm ${isUser ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-100' : 'bg-[#161618] border-[#27272a] text-[#f4f4f5]'}`}>
                                        <div className="prose prose-invert prose-sm max-w-none prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/5">
                                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    </div>
                                    <span className="text-[10px] text-zinc-600 mt-1 font-mono">{new Date(msg.timestamp).toLocaleTimeString()}</span>
                                </div>
                            );
                        }

                        // 4. Fallback for Unknown Events
                        return <GenericEvent key={i} role={msg.role} content={msg.content} timestamp={msg.timestamp} />;
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
