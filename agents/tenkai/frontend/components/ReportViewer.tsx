'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExperimentRecord, Checkpoint, RunResultRecord } from "@/app/api/api";
import MetricsOverview from "./experiments/MetricsOverview";
import PerformanceTable from "./experiments/PerformanceTable";
import RunHistory from "./experiments/RunHistory";
import RunDetails from "./experiments/RunDetails";
import ToolUsageTable from "./experiments/ToolUsageTable"; // Added
import ToolInspectionModal from "./experiments/ToolInspectionModal";
import ValidationModal from "./experiments/ValidationModal";
import FailureAnalysis from "./experiments/FailureAnalysis";
import StatusBanner from "./experiments/StatusBanner";
import { Button } from "./ui/button";
import RelaunchButton from "./RelaunchButton";
import KillExperimentButton from "./KillExperimentButton";

interface ReportViewerProps {
    experiment: ExperimentRecord;
    initialContent: string;
    initialMetrics: any;
    initialCheckpoint: Checkpoint | null;
    runResults: RunResultRecord[];
    stats: any;
    config: any;
    configContent: string;
}

export default function ReportViewer({
    experiment,
    initialContent,
    initialMetrics,
    initialCheckpoint,
    runResults,
    stats,
    config,
    configContent
}: ReportViewerProps) {
    const [activeTab, setActiveTab] = useState<'overview' | 'investigate' | 'config'>('overview');
    const [selectedRun, setSelectedRun] = useState<RunResultRecord | null>(null);
    const [inspectedTool, setInspectedTool] = useState<any>(null);
    const [inspectedValidation, setInspectedValidation] = useState<any>(null);
    const [configModalContent, setConfigModalContent] = useState<{ title: string, content: string } | null>(null);

    // Fetch run details when a run is selected
    const [runDetails, setRunDetails] = useState<any>(null);
    const [loadingDetails, setLoadingDetails] = useState(false);

    useEffect(() => {
        if (!selectedRun) {
            setRunDetails(null);
            return;
        }
        const fetchRunDetails = async () => {
            setLoadingDetails(true);
            try {
                const fetchSafe = async (url: string) => {
                    const r = await fetch(url);
                    if (!r.ok) return [];
                    return r.json();
                };

                const [tools, messages, files, tests, lints] = await Promise.all([
                    fetchSafe(`/api/runs/${selectedRun.id}/tools`),
                    fetchSafe(`/api/runs/${selectedRun.id}/messages`),
                    fetchSafe(`/api/runs/${selectedRun.id}/files`),
                    fetchSafe(`/api/runs/${selectedRun.id}/tests`),
                    fetchSafe(`/api/runs/${selectedRun.id}/lint`)
                ]);

                setRunDetails({ tools, messages, files, tests, lints });
            } catch (e) {

                console.error("Failed to fetch run details", e);
            } finally {
                setLoadingDetails(false);
            }
        };

        // Initial fetch
        fetchRunDetails();

        // Polling if running
        let interval: NodeJS.Timeout;
        if (selectedRun.status === 'running') {
            interval = setInterval(fetchRunDetails, 1000);
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [selectedRun]);

    return (
        <div className="flex flex-col h-full bg-[#0c0c0e] text-body">
            {/* Workbench Tab Bar */}
            <div className="flex justify-between items-center px-4 h-[56px] border-b border-[#27272a] bg-[#09090b]">
                <div className="flex h-full">
                    {[
                        { id: 'overview', label: 'Overview' },
                        { id: 'investigate', label: 'Investigate' },
                        { id: 'config', label: 'Configuration' }
                    ].map(tab => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id as any)}
                            className={`px-6 h-full font-bold uppercase tracking-widest transition-all border-b-2 ${activeTab === tab.id
                                ? "border-[#6366f1] text-[#f4f4f5]"
                                : "border-transparent text-[#52525b] hover:text-[#a1a1aa]"
                                }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>

                <div className="flex gap-2">
                    <Link href={`/api/experiments/${experiment.id}/export`} target="_blank">
                        <Button variant="outline" size="sm">
                            <span className="mr-2">📄</span> Export MD
                        </Button>
                    </Link>
                    <RelaunchButton experimentId={experiment.id} />
                    <KillExperimentButton experimentId={experiment.id} />
                </div>
            </div>

            {/* Content Stage */}
            <div className="flex-1 overflow-y-auto">
                <StatusBanner checkpoint={initialCheckpoint} />

                <div className="p-6">
                    {activeTab === 'overview' && (
                        <div className="space-y-8 animate-in fade-in duration-500">
                            {experiment.ai_analysis && (
                                <div className="panel p-8 bg-indigo-600/[0.03] border-indigo-500/10">
                                    <div className="flex items-center gap-2 mb-6">
                                        <span className="text-header">✨</span>
                                        <h3 className="text-header font-black uppercase tracking-tighter text-indigo-400">Executive Summary</h3>
                                    </div>
                                    <div className="prose prose-invert prose-lg max-w-none prose-headings:text-indigo-300">
                                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{experiment.ai_analysis}</ReactMarkdown>
                                    </div>
                                </div>
                            )}

                            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
                                <div className="lg:col-span-12">
                                    <MetricsOverview metrics={initialMetrics} />
                                </div>
                                <div className="lg:col-span-12">
                                    <PerformanceTable 
                                        runResults={runResults} 
                                        stats={stats} 
                                        controlBaseline={experiment.experiment_control}
                                        alternatives={config?.alternatives?.map((a: any) => a.name)}
                                    />

                                    <ToolUsageTable
                                        experimentId={experiment.id}
                                        alternatives={config?.alternatives?.map((a: any) => a.name) || Object.keys(stats).sort()}
                                    />

                                </div>
                                <div className="lg:col-span-12">
                                    <FailureAnalysis runs={runResults} />
                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'investigate' && (
                        <div className="flex h-[calc(100vh-200px)] gap-6 animate-in fade-in duration-500">
                            <div className="w-[350px] flex-shrink-0 panel bg-[#09090b]">
                                <RunHistory
                                    runs={runResults}
                                    selectedRunId={selectedRun?.id || null}
                                    onSelectRun={setSelectedRun}
                                />
                            </div>
                            <div className="flex-1 overflow-y-auto panel bg-[#0c0c0e] p-6">
                                {selectedRun ? (
                                    loadingDetails ? (
                                        <div className="flex items-center justify-center h-full animate-pulse">
                                            <p className="text-header uppercase font-bold text-zinc-700 tracking-widest">Loading Telemetry...</p>
                                        </div>
                                    ) : runDetails ? (
                                        <RunDetails
                                            run={selectedRun}
                                            details={runDetails}
                                            onInspectTool={setInspectedTool}
                                            onInspectValidation={setInspectedValidation}
                                        />
                                    ) : null
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-center opacity-30">
                                        <div className="text-6xl mb-4">🔍</div>
                                        <h3 className="text-header font-bold uppercase tracking-widest">Select a run to investigate</h3>
                                        <p>Browse the repetitions on the left to see full trace and file snapshots.</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                    {activeTab === 'config' && (
                        <div className="animate-in fade-in duration-500">
                            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                                {config?.alternatives?.map((alt: any, i: number) => {
                                    const isControl = alt.name === config.experiment_control;
                                    const altColors = [
                                        "border-indigo-500/30 bg-indigo-500/5",
                                        "border-emerald-500/30 bg-emerald-500/5",
                                        "border-amber-500/30 bg-amber-500/5",
                                        "border-rose-500/30 bg-rose-500/5",
                                        "border-cyan-500/30 bg-cyan-500/5",
                                        "border-violet-500/30 bg-violet-500/5",
                                        "border-orange-500/30 bg-orange-500/5",
                                        "border-lime-500/30 bg-lime-500/5",
                                        "border-fuchsia-500/30 bg-fuchsia-500/5",
                                        "border-sky-500/30 bg-sky-500/5",
                                    ];
                                    const containerClass = isControl 
                                        ? 'border-indigo-500/50 shadow-[0_0_20px_-10px_#6366f1] bg-indigo-900/10' 
                                        : altColors[i % altColors.length];

                                    return (
                                        <div key={i} className={`panel overflow-hidden flex flex-col ${containerClass}`}>
                                            <div className={`p-4 border-b flex justify-between items-center ${isControl ? 'border-indigo-500/20 bg-indigo-500/10' : 'border-white/5 bg-white/[0.02]'}`}>
                                                <div className="flex items-center gap-3">
                                                    <div className={`w-8 h-8 rounded flex items-center justify-center font-bold text-lg ${isControl ? 'bg-indigo-500 text-white' : 'bg-zinc-800 text-zinc-400'}`}>
                                                        {i + 1}
                                                    </div>
                                                    <div>
                                                        <h3 className={`font-bold text-lg ${isControl ? 'text-indigo-400' : 'text-white'}`}>{alt.name}</h3>
                                                        {isControl && <span className="text-xs uppercase font-bold tracking-widest text-indigo-300 opacity-70">Control Baseline</span>}
                                                    </div>
                                                </div>
                                                {alt.description && <span className="text-zinc-500 text-sm italic" title={alt.description}>{alt.description}</span>}
                                            </div>
                                            <div className="p-6 space-y-6 flex-1 bg-transparent">
                                                {/* Command */}
                                                <div className="space-y-2">
                                                    <p className="text-xs font-bold uppercase tracking-widest text-[#52525b]">Execution Command</p>
                                                    <div className="font-mono text-sm bg-black/40 p-3 rounded border border-white/5 text-zinc-300 break-all cursor-default">
                                                        <span className="text-emerald-400 font-bold">{alt.command}</span> {alt.args?.join(' ')} <span className="text-zinc-500 italic">&lt;PROMPT&gt;</span>
                                                    </div>
                                                </div>

                                                {/* Settings / Prompt / Context */}

                                                <div className="grid grid-cols-2 gap-4">
                                                    <div className="space-y-2">
                                                        <p className="text-xs font-bold uppercase tracking-widest text-[#52525b]">System Prompt</p>
                                                        {alt.system_prompt_file ? (
                                                            <div 
                                                                className="flex items-center gap-2 text-indigo-400 font-mono text-sm cursor-pointer hover:underline"
                                                                onClick={() => setConfigModalContent({
                                                                    title: `System Prompt Path: ${alt.name}`,
                                                                    content: `Loaded from: ${alt.system_prompt_file}`
                                                                })}
                                                            >
                                                                <span className="w-2 h-2 rounded-full bg-indigo-500"></span>
                                                                {alt.system_prompt_file.split('/').pop()}
                                                            </div>
                                                        ) : (
                                                            <div 
                                                                className={`text-sm ${alt.system_prompt ? 'text-indigo-400 cursor-pointer hover:underline' : 'text-zinc-600 italic'}`}
                                                                onClick={() => alt.system_prompt && setConfigModalContent({
                                                                    title: `System Prompt: ${alt.name}`,
                                                                    content: alt.system_prompt
                                                                })}
                                                            >
                                                                {alt.system_prompt ? "Inline Prompt" : "Default (No override)"}
                                                            </div>
                                                        )}
                                                    </div>

                                                    <div className="space-y-2">
                                                        <p className="text-xs font-bold uppercase tracking-widest text-[#52525b]">GEMINI.md (Context)</p>
                                                        {alt.context_file_path ? (
                                                            <div 
                                                                className="flex items-center gap-2 text-emerald-400 font-mono text-sm cursor-pointer hover:underline"
                                                                onClick={() => setConfigModalContent({
                                                                    title: `Context Path: ${alt.name}`,
                                                                    content: `Loaded from: ${alt.context_file_path}`
                                                                })}
                                                            >
                                                                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                                                                {alt.context_file_path.split('/').pop()}
                                                            </div>
                                                        ) : alt.context ? (
                                                            <div 
                                                                className="flex items-center gap-2 text-emerald-400 font-mono text-sm cursor-pointer hover:underline"
                                                                onClick={() => setConfigModalContent({
                                                                    title: `Context Content: ${alt.name}`,
                                                                    content: alt.context
                                                                })}
                                                            >
                                                                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                                                                Custom Context
                                                            </div>
                                                        ) : (
                                                            <div className="text-zinc-600 italic text-sm">None</div>
                                                        )}
                                                    </div>

                                                    <div className="space-y-2">
                                                        <p className="text-xs font-bold uppercase tracking-widest text-[#52525b]">Settings</p>
                                                        {alt.settings_path ? (
                                                            <div 
                                                                className="flex items-center gap-2 text-amber-400 font-mono text-sm cursor-pointer hover:underline"
                                                                onClick={() => setConfigModalContent({
                                                                    title: `Settings Path: ${alt.name}`,
                                                                    content: `Loaded from: ${alt.settings_path}`
                                                                })}
                                                            >
                                                                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                                                {alt.settings_path.split('/').pop()}
                                                            </div>
                                                        ) : alt.settings && Object.keys(alt.settings).length > 0 ? (
                                                            <div 
                                                                className="flex items-center gap-2 text-amber-400 font-mono text-sm cursor-pointer hover:underline"
                                                                onClick={() => setConfigModalContent({
                                                                    title: `Settings: ${alt.name}`,
                                                                    content: JSON.stringify(alt.settings, null, 2)
                                                                })}
                                                            >
                                                                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                                                                Custom Profile
                                                            </div>
                                                        ) : (
                                                            <div className="text-zinc-600 italic text-sm">Standard Profile</div>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                </div>
            </div>

            <ToolInspectionModal tool={inspectedTool} onClose={() => setInspectedTool(null)} />
            <ValidationModal item={inspectedValidation} onClose={() => setInspectedValidation(null)} />

            {configModalContent && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200" onClick={() => setConfigModalContent(null)}>
                    <div className="bg-[#161618] border border-[#27272a] rounded-lg shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center p-4 border-b border-[#27272a]">
                            <h3 className="font-bold uppercase tracking-widest text-[#f4f4f5]">{configModalContent.title}</h3>
                            <button onClick={() => setConfigModalContent(null)} className="text-zinc-500 hover:text-white transition-colors">✕</button>
                        </div>
                        <div className="p-6 overflow-auto font-mono text-sm text-zinc-300 whitespace-pre-wrap">
                            {configModalContent.content}
                        </div>
                    </div>
                </div>
            )}
        </div >
    );
}

