'use client';

import { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExperimentRecord, Checkpoint, RunResultRecord, getRunResults, reValidateExperiment } from "@/app/api/api";
import { Loader2, RefreshCw } from "lucide-react";
import MetricsOverview from "./experiments/MetricsOverview";
import PerformanceTable from "./experiments/PerformanceTable";
import RunHistory from "./experiments/RunHistory";
import RunDetails from "./experiments/RunDetails";
import ToolUsageTable from "./experiments/ToolUsageTable";
import ToolImpactTable from "./experiments/ToolImpactTable";
import ToolInspectionModal from "./experiments/ToolInspectionModal";
import ValidationModal from "./experiments/ValidationModal";
import FailureAnalysis from "./experiments/FailureAnalysis";
import StatusBanner from "./experiments/StatusBanner";
import { Button } from "./ui/button";
import RelaunchButton from "./RelaunchButton";
import KillExperimentButton from "./KillExperimentButton";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { toast } from "sonner";
import ProgressBar from "./ui/progress-bar";

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

function RevalidateExperimentButton({ experimentId, isExperimentRunning, onStateChange }: { experimentId: number, isExperimentRunning: boolean, onStateChange?: (revalidating: boolean) => void }) {
    const [loading, setLoading] = useState(false);
    const [jobId, setJobId] = useState<string | null>(null);
    const [progress, setProgress] = useState(0);
    const [stats, setStats] = useState<{ completed: number, total: number } | null>(null);
    const isProcessing = useRef(false);
    const router = useRouter();

    // Poll job status
    useEffect(() => {
        if (!jobId) {
            isProcessing.current = false;
            return;
        }

        const interval = setInterval(async () => {
            if (isProcessing.current) return;

            try {
                const res = await fetch(`/api/jobs/${jobId}`);
                if (!res.ok) return;
                const job = await res.json();

                // If job ID changed or was cleared by another tick in the meantime
                if (!jobId) return;

                setProgress(job.progress);
                setStats({ completed: job.completed, total: job.total });

                if (job.status === "COMPLETED" || job.status === "FAILED") {
                    isProcessing.current = true;
                    clearInterval(interval);
                    setJobId(null);
                    setLoading(false);
                    onStateChange?.(false);

                    if (job.status === "COMPLETED") {
                        toast.success("Re-validation completed!");
                        router.refresh();
                    } else {
                        toast.error(`Re-validation failed: ${job.error}`);
                    }
                }
            } catch (e) {
                console.error("Polling job failed", e);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [jobId]);

    const handleReval = async () => {
        toast("Start re-validation for ALL completed runs?", {
            action: {
                label: "Run Now",
                onClick: async () => {
                    setLoading(true);
                    onStateChange?.(true);
                    try {
                        const res = await reValidateExperiment(experimentId);
                        if (res && res.job_id) {
                            setJobId(res.job_id);
                            toast.info("Re-evaluation started...");
                        } else if (res && res.error) {
                            toast.error(`Re-evaluation failed: ${res.error}`);
                            setLoading(false);
                            onStateChange?.(false);
                        } else {
                            console.error("Unexpected reval response:", res);
                            toast.error(`Re-evaluation started but no JobID was returned.`);
                            setLoading(false);
                            onStateChange?.(false);
                        }
                    } catch (e: any) {
                        toast.error("Failed to start re-evaluation: " + e.message);
                        setLoading(false);
                        onStateChange?.(false);
                    }
                }
            }
        });
    };



    if (jobId) {
        return (
            <div className="flex flex-col gap-1 w-[200px]">
                <ProgressBar
                    percentage={progress}
                    completed={stats?.completed || 0}
                    total={stats?.total || 0}
                    status="RUNNING"
                    showLabel={true}
                />
                <span className="text-[10px] text-zinc-500 uppercase font-bold text-center">Re-validating...</span>
            </div>
        )
    }

    return (
        <Button variant="outline" size="sm" onClick={handleReval} disabled={loading || isExperimentRunning}>
            {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCw className="mr-2 h-4 w-4" />}
            {loading ? "Starting..." : "Re-validate Failures"}
        </Button>
    );
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
    const router = useRouter();
    const searchParams = useSearchParams();
    const pathname = usePathname();

    const activeTab = (searchParams.get('tab') as 'overview' | 'investigate' | 'config') || 'overview';
    const runIdFromUrl = searchParams.get('runId');

    const [selectedRun, setSelectedRun] = useState<RunResultRecord | null>(null);
    const [inspectedTool, setInspectedTool] = useState<any>(null);
    const [inspectedValidation, setInspectedValidation] = useState<any>(null);
    const [configModalContent, setConfigModalContent] = useState<{ title: string, content: string } | null>(null);
    const [isRevalidating, setIsRevalidating] = useState(false);

    const isRunning = experiment.status?.toUpperCase() === 'RUNNING';

    // Pagination State
    const [runs, setRuns] = useState<RunResultRecord[]>(runResults);
    const [page, setPage] = useState(1);
    const [hasMore, setHasMore] = useState(true); // Assume true initially if we have results
    const [loadingRuns, setLoadingRuns] = useState(false);

    const loadMoreRuns = async () => {
        if (loadingRuns || !hasMore) return;
        setLoadingRuns(true);
        try {
            const nextPage = page + 1;
            const newRuns = await getRunResults(experiment.id, nextPage, 5000);
            if (newRuns.length < 5000) {
                setHasMore(false);
            }
            if (newRuns.length > 0) {
                setRuns(prev => [...prev, ...newRuns]);
                setPage(nextPage);
            }
        } catch (e) {
            console.error("Failed to load more runs", e);
        } finally {
            setLoadingRuns(false);
        }
    };

    // Check initial load size to set hasMore correctly
    useEffect(() => {
        if (runResults.length < 100) {
            setHasMore(false);
        }
    }, []);

    // Sync selectedRun with runId in URL
    useEffect(() => {
        if (runIdFromUrl) {
            const runId = parseInt(runIdFromUrl);
            const found = runs.find(r => r.id === runId);
            if (found && (!selectedRun || selectedRun.id !== runId)) {
                setSelectedRun(found);
            }
        } else if (selectedRun) {
            setSelectedRun(null);
        }
    }, [runIdFromUrl, runs]);

    const updateUrl = (params: { tab?: string, runId?: number | null }) => {
        const current = new URLSearchParams(searchParams.toString());
        if (params.tab) {
            current.set('tab', params.tab);
        }
        if (params.runId !== undefined) {
            if (params.runId === null) {
                current.delete('runId');
            } else {
                current.set('runId', params.runId.toString());
            }
        }
        router.push(`${pathname}?${current.toString()}`, { scroll: false });
    };

    const handleTabChange = (tabId: 'overview' | 'investigate' | 'config') => {
        updateUrl({ tab: tabId });
    };

    const handleSelectRun = (run: RunResultRecord) => {
        updateUrl({ tab: 'investigate', runId: run.id });
    };

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
            interval = setInterval(fetchRunDetails, 3000);
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
                            onClick={() => handleTabChange(tab.id as any)}
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
                    {runResults.some(r => r.reason === 'FAILED (VALIDATION)') && (
                        <RevalidateExperimentButton
                            experimentId={experiment.id}
                            isExperimentRunning={isRunning}
                            onStateChange={setIsRevalidating}
                        />
                    )}
                    <Link href={`/api/experiments/${experiment.id}/export`} target="_blank">
                        <Button variant="outline" size="sm">
                            <span className="mr-2">📄</span> Export MD
                        </Button>
                    </Link>

                    <RelaunchButton experimentId={experiment.id} disabled={isRunning} />
                    <KillExperimentButton experimentId={experiment.id} disabled={!isRunning} />
                </div>
            </div>

            {/* Content Stage */}
            <div className="flex-1 overflow-y-auto">
                <StatusBanner checkpoint={initialCheckpoint} />

                <div className="p-6">
                    {activeTab === 'overview' && (
                        <div className="space-y-8 animate-in fade-in duration-500">


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

                                    <ToolImpactTable
                                        stats={stats}
                                        alternatives={[...(config?.alternatives?.map((a: any) => a.name) || Object.keys(stats).sort()), "Combined"]}
                                    />

                                    <FailureAnalysis runs={runResults} stats={stats} />

                                    <ToolUsageTable
                                        experimentId={experiment.id}
                                        alternatives={config?.alternatives?.map((a: any) => a.name) || Object.keys(stats).sort()}
                                    />

                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'investigate' && (
                        <div className="flex h-[calc(100vh-200px)] gap-6 animate-in fade-in duration-500">
                            <div className="w-[350px] flex-shrink-0 panel bg-[#09090b]">
                                <RunHistory
                                    runs={runs}
                                    selectedRunId={selectedRun?.id || null}
                                    onSelectRun={handleSelectRun}
                                    onLoadMore={loadMoreRuns}
                                    hasMore={hasMore}
                                    loading={loadingRuns}
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
                                            key={selectedRun.id}
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
