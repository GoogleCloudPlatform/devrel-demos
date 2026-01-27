'use client';

import { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ExperimentRecord, Checkpoint, RunResultRecord, getRunResults, reValidateExperiment, getExperimentSummaries, ExperimentSummaryRecord } from "@/app/api/api";
import { ConfigBlock, ConfigBlockType } from "@/types/domain";
import { Loader2, RefreshCw, BarChart3 } from "lucide-react";
import { ToggleGroup, ToggleGroupItem } from "./ui/toggle-group";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
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
import AlternativeCard from "./AlternativeCard";

interface ReportViewerProps {
    experiment: ExperimentRecord;
    initialContent: string;
    initialMetrics: any;
    initialCheckpoint: Checkpoint | null;
    runResults: RunResultRecord[];
    stats: any;
    config: any;
    configContent: string;
    blocks: ConfigBlock[];
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
    configContent,
    blocks
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
    const [filterAlternative, setFilterAlternative] = useState<string | null>(null);
    const [filterMode, setFilterMode] = useState<string>("all");
    const [viewStats, setViewStats] = useState<any>(stats);

    // Sync stats when prop changes or filter changes
    useEffect(() => {
        // Initial sync from props
        if (filterMode === 'all' && stats && Object.keys(stats).length > 0) {
            setViewStats(stats);
        }
    }, [stats]);

    const handleFilterChange = async (val: string) => {
        if (!val) return;
        setFilterMode(val);
        // Fetch new summaries
        try {
            const newSummaries = await getExperimentSummaries(experiment.id, val);
            const statObj: any = {};
            newSummaries.forEach((row: ExperimentSummaryRecord) => {
                statObj[row.alternative] = { ...row, alternative: row.alternative, count: row.total_runs };
            });
            setViewStats(statObj);
        } catch (e) {
            console.error("Failed to fetch filtered stats", e);
            toast.error("Failed to update statistics");
        }
    };

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
        // Sync local state if prop updates (e.g. from polling in parent)
        setRuns(runResults);
    }, [runResults]);

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

    const handleAlternativeClick = (alt: string) => {
        setFilterAlternative(alt);
        handleTabChange('investigate');
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


    // Helper to get selected block ID/Name for dropdowns
    const getSelectedBlockName = (type: ConfigBlockType, content: any) => {
        if (!content) return "(none selected)";
        // Content might be a string (system prompt) or object (agent).
        const contentStr = typeof content === 'string' ? content : JSON.stringify(content);

        const match = blocks.find(b => {
            if (b.type !== type) return false;
            // Compare parsed if JSON, raw if text
            if (type === 'system_prompt' || type === 'context') {
                return b.content.trim() === contentStr.trim();
            }
            try {
                const bContent = JSON.parse(b.content);
                const cContent = typeof content === 'string' ? JSON.parse(content) : content;
                return JSON.stringify(bContent) === JSON.stringify(cContent);
            } catch {
                return b.content === contentStr;
            }
        });
        return match ? match.name : (content ? "Custom/Manual" : "(none selected)");
    };

    // For Agent specifically, we check command/args match
    const getAgentBlockName = (alt: any) => {
        if (!alt.command) return "(Select Agent)";
        const match = blocks.find(b => {
            if (b.type !== 'agent') return false;
            try {
                const c = JSON.parse(b.content);
                // Compare command and args
                // args might be string or array
                const bArgs = Array.isArray(c.args) ? c.args.join(" ") : (c.args || "");
                const altArgs = Array.isArray(alt.args) ? alt.args.join(" ") : (alt.args || "");
                return c.command === alt.command && bArgs === altArgs;
            } catch { return false; }
        });
        return match ? match.name : `${alt.command} (Custom)`;
    };


    return (
        <div className="flex flex-col h-full bg-background text-body">
            {/* Workbench Tab Bar */}
            <div className="flex justify-between items-center px-4 h-[56px] border-b border-border bg-card">
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
                                ? "border-primary text-foreground"
                                : "border-transparent text-muted-foreground hover:text-foreground"
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
                                    <div className="flex justify-between items-center mb-4">
                                        <h3 className="font-bold uppercase tracking-widest text-muted-foreground text-sm flex items-center gap-2">
                                            <BarChart3 className="w-4 h-4" /> Performance Analysis
                                        </h3>
                                        <ToggleGroup type="single" value={filterMode} onValueChange={handleFilterChange} className="bg-muted/30 p-1 rounded-lg border border-white/5">
                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <div>
                                                        <ToggleGroupItem value="all" aria-label="All Runs" className="text-xs data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm transition-all h-7 px-3">
                                                            <RefreshCw className="mr-1 h-3 w-3" />
                                                            All Runs
                                                        </ToggleGroupItem>
                                                    </div>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p>Includes all completed runs, timeouts, and system errors.</p>
                                                </TooltipContent>
                                            </Tooltip>

                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <div>
                                                        <ToggleGroupItem value="completed" aria-label="Completed Only" className="text-xs data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm transition-all h-7 px-3">
                                                            <BarChart3 className="mr-1 h-3 w-3" />
                                                            Completed Only
                                                        </ToggleGroupItem>
                                                    </div>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p>Excludes timeouts and crashes. Only Success + Validation Failures.</p>
                                                </TooltipContent>
                                            </Tooltip>

                                            <Tooltip>
                                                <TooltipTrigger asChild>
                                                    <div>
                                                        <ToggleGroupItem value="successful" aria-label="Successful Only" className="text-xs data-[state=on]:bg-background data-[state=on]:text-foreground data-[state=on]:shadow-sm transition-all h-7 px-3">
                                                            <span className="mr-1">✨</span>
                                                            Successful Only
                                                        </ToggleGroupItem>
                                                    </div>
                                                </TooltipTrigger>
                                                <TooltipContent>
                                                    <p>Strictly excludes all failures.</p>
                                                </TooltipContent>
                                            </Tooltip>
                                        </ToggleGroup>
                                    </div>
                                    <PerformanceTable
                                        runResults={runResults}
                                        stats={viewStats}
                                        controlBaseline={experiment.experiment_control}
                                        alternatives={config?.alternatives?.map((a: any) => a.name)}
                                        onAlternativeClick={handleAlternativeClick}
                                    />

                                    <ToolImpactTable
                                        stats={viewStats}
                                        alternatives={[...(config?.alternatives?.map((a: any) => a.name) || Object.keys(stats).sort()), "Combined"]}
                                    />

                                    <FailureAnalysis runs={runResults} stats={viewStats} />

                                    <ToolUsageTable
                                        experimentId={experiment.id}
                                        alternatives={config?.alternatives?.map((a: any) => a.name) || Object.keys(stats).sort()}
                                        filter={filterMode}
                                    />

                                </div>
                            </div>
                        </div>
                    )}

                    {activeTab === 'investigate' && (
                        <div className="flex h-[calc(100vh-200px)] gap-6 animate-in fade-in duration-500">
                            <div className="w-[350px] flex-shrink-0 panel bg-card">
                                <RunHistory
                                    runs={runs}
                                    selectedRunId={selectedRun?.id || null}
                                    onSelectRun={handleSelectRun}
                                    onLoadMore={loadMoreRuns}
                                    hasMore={hasMore}
                                    loading={loadingRuns}
                                    filterAlternative={filterAlternative}
                                    onClearFilter={() => setFilterAlternative(null)}
                                />
                            </div>
                            <div className="flex-1 overflow-y-auto panel bg-card p-6">
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
                                    return (
                                        <AlternativeCard
                                            key={i}
                                            alt={alt}
                                            index={i}
                                            blocks={blocks}
                                            isControl={alt.name === config.experiment_control}
                                            onUpdate={() => { }} // Read-only
                                            onSetControl={() => { }} // Read-only
                                            onDelete={() => { }} // Read-only
                                            onDuplicate={() => { }} // Read-only
                                            getAgentName={() => getAgentBlockName(alt)}
                                            getBlockName={(t, c) => getSelectedBlockName(t, c)}
                                            isLocked={true}
                                        />
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
                    <div className="bg-popover border border-border rounded-lg shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
                        <div className="flex justify-between items-center p-4 border-b border-border">
                            <h3 className="font-bold uppercase tracking-widest text-foreground">{configModalContent.title}</h3>
                            <button onClick={() => setConfigModalContent(null)} className="text-muted-foreground hover:text-foreground transition-colors">✕</button>
                        </div>
                        <div className="p-6 overflow-auto font-mono text-sm text-muted-foreground whitespace-pre-wrap">
                            {configModalContent.content}
                        </div>
                    </div>
                </div>
            )}
        </div >
    );
}

