'use client';

import { useState, useEffect } from 'react';
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Checkpoint, ExperimentRecord } from '@/lib/api';
import { welchTTest, zTestProportions } from "@/lib/statistics";

interface ReportViewerProps {
    experiment: ExperimentRecord;
    initialContent: string;
    initialMetrics: any;
    initialCheckpoint: Checkpoint | null;
    runResults: any[];
    stats: any;
    config: any;
    configContent?: string;
}

function DiffValue({ label, current, reference, isFile = false, showIdentical = false }: { label: string, current: any, reference: any, isFile?: boolean, showIdentical?: boolean }) {
    const isDifferent = JSON.stringify(current) !== JSON.stringify(reference);

    if (!isDifferent && !showIdentical) return null;

    if (isFile && showIdentical) {
        const lines = String(current || '').split('\n');
        return (
            <div className="space-y-2">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{label}</h4>
                <div className="rounded-xl border border-white/5 overflow-hidden bg-black/40">
                    <div className="bg-white/5 border-b border-white/5 px-4 py-2">
                        <p className="text-[9px] text-zinc-500 uppercase font-black tracking-widest">Control Baseline</p>
                    </div>
                    <pre className="p-4 text-xs font-mono text-zinc-300 whitespace-pre overflow-x-auto max-h-80 overflow-y-auto leading-relaxed">
                        {lines.map((line, i) => (
                            <div key={i}>{line || ' '}</div>
                        ))}
                    </pre>
                </div>
            </div>
        );
    }

    if (isFile && isDifferent && !showIdentical) {
        const refLines = String(reference || '').split('\n');
        const curLines = String(current || '').split('\n');
        const maxLines = Math.max(refLines.length, curLines.length);

        return (
            <div className="space-y-2">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{label}</h4>
                <div className="rounded-xl border border-blue-500/20 overflow-hidden bg-black/40">
                    <div className="grid grid-cols-2 bg-white/5 border-b border-white/5 px-4 py-2">
                        <p className="text-[9px] text-zinc-500 uppercase font-black tracking-widest">Baseline (Control)</p>
                        <p className="text-[9px] text-blue-400 uppercase font-black tracking-widest">Selected Alternative</p>
                    </div>
                    <div className="grid grid-cols-2 divide-x divide-white/5 max-h-80 overflow-y-auto">
                        <div className="min-w-0 overflow-hidden">
                            <pre className="p-4 text-xs font-mono text-zinc-500 whitespace-pre overflow-x-auto leading-relaxed">
                                {(() => {
                                    const rendered = [];
                                    let skipping = false;
                                    for (let i = 0; i < maxLines; i++) {
                                        const line1 = refLines[i] || '';
                                        const line2 = curLines[i] || '';
                                        const isDiff = line1 !== line2;
                                        if (isDiff) {
                                            rendered.push(
                                                <div key={i} className="bg-red-500/10 text-red-300 -mx-4 px-4">
                                                    {line1 || ' '}
                                                </div>
                                            );
                                            skipping = false;
                                        } else if (!skipping) {
                                            rendered.push(<div key={`skip-${i}`} className="text-zinc-700 px-2 py-0.5 text-[10px] italic">... identical lines hidden ...</div>);
                                            skipping = true;
                                        }
                                    }
                                    return rendered;
                                })()}
                            </pre>
                        </div>
                        <div className="min-w-0 overflow-hidden">
                            <pre className="p-4 text-xs font-mono text-zinc-300 whitespace-pre overflow-x-auto leading-relaxed">
                                {(() => {
                                    const rendered = [];
                                    let skipping = false;
                                    for (let i = 0; i < maxLines; i++) {
                                        const line1 = refLines[i] || '';
                                        const line2 = curLines[i] || '';
                                        const isDiff = line1 !== line2;
                                        if (isDiff) {
                                            rendered.push(
                                                <div key={i} className="bg-emerald-500/10 text-emerald-400 -mx-4 px-4 font-bold">
                                                    {line2 || ' '}
                                                </div>
                                            );
                                            skipping = false;
                                        } else if (!skipping) {
                                            rendered.push(<div key={`skip-${i}`} className="text-zinc-700 px-2 py-0.5 text-[10px] italic">... identical lines hidden ...</div>);
                                            skipping = true;
                                        }
                                    }
                                    return rendered;
                                })()}
                            </pre>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    if (showIdentical) {
        return (
            <div className="space-y-2">
                <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{label}</h4>
                <div className="space-y-1">
                    <p className="text-[9px] text-zinc-600 uppercase font-black tracking-tighter">Control Value</p>
                    <pre className={`p-3 rounded-xl bg-black/40 border border-white/5 text-xs font-mono overflow-x-auto ${isFile ? 'whitespace-pre-wrap max-h-40 overflow-y-auto' : ''}`}>
                        {typeof current === 'object' ? JSON.stringify(current, null, 2) : String(current || 'None')}
                    </pre>
                </div>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">{label}</h4>
            <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                    <p className="text-[9px] text-zinc-600 uppercase font-black tracking-tighter">Baseline (Control)</p>
                    <pre className={`p-3 rounded-xl bg-black/40 border border-white/5 text-xs font-mono overflow-x-auto ${isFile ? 'whitespace-pre-wrap max-h-40 overflow-y-auto' : ''}`}>
                        {typeof reference === 'object' ? JSON.stringify(reference, null, 2) : String(reference || 'None')}
                    </pre>
                </div>
                <div className="space-y-1">
                    <p className="text-[9px] text-zinc-600 uppercase font-black tracking-tighter">Selected Alternative</p>
                    <pre className={`p-3 rounded-xl text-xs font-mono border overflow-x-auto bg-blue-500/10 border-blue-500/20 text-blue-100 ${isFile ? 'whitespace-pre-wrap max-h-40 overflow-y-auto' : ''}`}>
                        {typeof current === 'object' ? JSON.stringify(current, null, 2) : String(current || 'None')}
                    </pre>
                </div>
            </div>
        </div>
    );
}

function ConfigDiffView({ selectedAlt, controlAlt, fileContents, loadingFiles }: { selectedAlt: any, controlAlt: any, fileContents: Record<string, string>, loadingFiles: boolean }) {
    if (!selectedAlt || !controlAlt) return null;

    const isControl = selectedAlt.name === controlAlt.name;

    const getFileDisplay = (path?: string) => {
        if (!path) return 'None';
        if (loadingFiles && !fileContents[path]) return 'Loading...';
        return fileContents[path] || `File not found: ${path}`;
    };

    const diffs = [
        <DiffValue key="cmd" label="Command" current={selectedAlt.command} reference={controlAlt.command} showIdentical={isControl} />,
        <DiffValue key="args" label="Arguments" current={selectedAlt.args} reference={controlAlt.args} showIdentical={isControl} />,
        <DiffValue key="env" label="Environment" current={selectedAlt.env} reference={controlAlt.env} showIdentical={isControl} />,
    ].filter(Boolean);

    const fileDiffs = [
        <DiffValue
            key="prompt"
            label={`System Prompt (${selectedAlt.system_prompt_file || 'Standard'})`}
            current={getFileDisplay(selectedAlt.system_prompt_file)}
            reference={getFileDisplay(controlAlt.system_prompt_file)}
            isFile={true}
            showIdentical={isControl}
        />,
        <DiffValue
            key="settings"
            label={`Settings (${selectedAlt.settings_path || 'Default'})`}
            current={getFileDisplay(selectedAlt.settings_path)}
            reference={getFileDisplay(controlAlt.settings_path)}
            isFile={true}
            showIdentical={isControl}
        />,
        <DiffValue
            key="context"
            label={`Context File (${selectedAlt.context_file_path || 'None'})`}
            current={getFileDisplay(selectedAlt.context_file_path)}
            reference={getFileDisplay(controlAlt.context_file_path)}
            isFile={true}
            showIdentical={isControl}
        />
    ].filter(Boolean);

    if (!isControl && diffs.length === 0 && fileDiffs.length === 0) {
        return (
            <div className="text-sm text-zinc-500 italic py-4">
                This alternative is configurationally identical to the control baseline.
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6">
                {diffs}

                {fileDiffs.length > 0 && (
                    <div className="border-t border-white/5 pt-6">
                        <h3 className="text-xs font-black text-zinc-400 uppercase tracking-[0.2em] mb-4">File Content Diffs</h3>
                        <div className="space-y-6">
                            {fileDiffs}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}

export default function ReportViewer({ experiment, initialContent, initialMetrics, initialCheckpoint, runResults, stats, config, configContent }: ReportViewerProps) {
    const [tab, setTab] = useState<'analytics' | 'history' | 'config'>('analytics');
    const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(initialCheckpoint);
    const [status, setStatus] = useState(experiment.status);
    const [metrics, setMetrics] = useState(initialMetrics);
    const [aiAnalysis, setAiAnalysis] = useState<string | null>(experiment.ai_analysis || null);
    const [loadingAction, setLoadingAction] = useState<string | null>(null);
    const [selectedRun, setSelectedRun] = useState<any>(null);
    const [runDetails, setRunDetails] = useState<{ tools: any[], messages: any[], files: any[], tests: any[], lints: any[] } | null>(null);
    const [selectedFile, setSelectedFile] = useState<any>(null);
    const [loadingDetails, setLoadingDetails] = useState(false);
    const [inspectingTool, setInspectingTool] = useState<any>(null);
    const [inspectingFile, setInspectingFile] = useState<any>(null);
    const [inspectingValidation, setInspectingValidation] = useState<any>(null);
    const [inspectingTest, setInspectingTest] = useState<any>(null);
    const [selectedAlternative, setSelectedAlternative] = useState<string | null>(null);

    // Config Diff State
    const [fileContents, setFileContents] = useState<Record<string, string>>({});
    const [loadingFiles, setLoadingFiles] = useState(false);

    // Derived Logic
    const altNames = Object.keys(stats);
    const referenceAlt = experiment.experiment_control || config?.alternatives?.[0]?.name || altNames[0];
    const refStats = stats[referenceAlt];

    // Sync state with props when server refreshes
    useEffect(() => { setMetrics(initialMetrics); }, [initialMetrics]);
    useEffect(() => { setStatus(experiment.status); }, [experiment.status]);

    useEffect(() => {
        if (status === 'running' || status === 'paused') {
            const interval = setInterval(async () => {
                try {
                    const res = await fetch(`/api/experiments/checkpoint?id=${experiment.id}`);
                    if (res.ok) {
                        const data = await res.json();
                        setCheckpoint(data);
                        if (data.status !== status) {
                            setStatus(data.status);
                        }

                        // Always refresh metrics when running to show live simplified stats (duration, lint, etc.)
                        const mRes = await fetch(`/api/experiments/metrics?id=${experiment.id}`);
                        if (mRes.ok) setMetrics(await mRes.json());

                        if (data.status === 'completed' || data.status === 'stopped' || data.status === 'failed') {
                            clearInterval(interval);
                        }
                    }
                } catch (e) {
                    console.error("Failed to poll checkpoint", e);
                }
            }, 2000);
            return () => clearInterval(interval);
        }
    }, [status, experiment.results_path, experiment.id]);

    const handleControl = async (action: 'pause' | 'resume' | 'stop') => {
        setLoadingAction(action);
        try {
            const res = await fetch('/api/experiments/control', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id: experiment.id, action }),
            });
            if (res.ok) {
                if (action === 'stop') setStatus('stopped');
                if (action === 'pause') setStatus('paused');
                if (action === 'resume') setStatus('running');
            } else {
                alert(`Failed to ${action} experiment`);
            }
        } catch (e) {
            console.error(e);
            alert(`Error sending ${action} command`);
        } finally {
            setLoadingAction(null);
        }
    };

    const fetchRunDetails = async (run: any) => {
        setSelectedRun(run);
        setLoadingDetails(true);
        try {
            const [tRes, mRes, fRes, testRes, lRes] = await Promise.all([
                fetch(`/api/runs/${run.id}/tools`),
                fetch(`/api/runs/${run.id}/messages`),
                fetch(`/api/runs/${run.id}/files`),
                fetch(`/api/runs/${run.id}/tests`),
                fetch(`/api/runs/${run.id}/lint`)
            ]);
            if (tRes.ok && mRes.ok && fRes.ok && testRes.ok && lRes.ok) {
                const tools = await tRes.json();
                const messages = await mRes.json();
                const files = await fRes.json();
                const tests = await testRes.json();
                const lints = await lRes.json();
                setRunDetails({ tools, messages, files, tests, lints });
                if (files.length > 0) setSelectedFile(files[0]);
            }
        } catch (e) {
            console.error("Failed to fetch run details", e);
        } finally {
            setLoadingDetails(false);
        }
    };

    const handleRegenerate = async () => {
        setLoadingAction('regenerate');
        try {
            const res = await fetch(`/api/experiments/${experiment.id}/regenerate`, { method: 'POST' });
            if (res.ok) {
                window.location.reload();
            } else {
                alert('Failed to regenerate report');
            }
        } catch (e) {
            console.error(e);
            alert('Error regenerating report');
        } finally {
            setLoadingAction(null);
        }
    };

    const handleExplain = async () => {
        setLoadingAction('explain');
        try {
            const res = await fetch(`/api/experiments/${experiment.id}/explain`, { method: 'POST' });
            if (res.ok) {
                const data = await res.json();
                setAiAnalysis(data.analysis);
            } else {
                const data = await res.json().catch(() => ({}));
                alert(`Failed to generate AI insights: ${data.error || 'Unknown server error'}`);
            }
        } catch (e) {
            console.error(e);
            alert('Error generating AI insights. Check console.');
        } finally {
            setLoadingAction(null);
        }
    };

    // Fetch config files for diff view
    useEffect(() => {
        const fetchFiles = async () => {
            if (!selectedAlternative || !config) return;

            const controlAltName = experiment.experiment_control || config.control || config.alternatives[0].name;
            const selectedAlt = config.alternatives.find((a: any) => a.name === selectedAlternative);
            const controlAlt = config.alternatives.find((a: any) => a.name === controlAltName);

            if (!selectedAlt || !controlAlt) return;

            setLoadingFiles(true);
            const pathsToFetch = new Set<string>();
            [selectedAlt, controlAlt].forEach(alt => {
                if (alt.system_prompt_file) pathsToFetch.add(alt.system_prompt_file);
                if (alt.settings_path) pathsToFetch.add(alt.settings_path);
                if (alt.context_file_path) pathsToFetch.add(alt.context_file_path);
            });

            const newContents: Record<string, string> = { ...fileContents };
            let changed = false;

            for (const filePath of pathsToFetch) {
                if (newContents[filePath]) continue;
                try {
                    const res = await fetch(`/api/experiments/${experiment.id}/files?path=${encodeURIComponent(filePath)}`);
                    if (res.ok) {
                        const data = await res.json();
                        newContents[filePath] = data.content;
                        changed = true;
                    }
                } catch (e) {
                    console.error(`Failed to fetch ${filePath}`, e);
                }
            }

            if (changed) setFileContents(newContents);
            setLoadingFiles(false);
        };

        fetchFiles();
    }, [selectedAlternative, config, experiment.id, experiment.experiment_control]);

    const isActive = status === 'running' || status === 'paused';

    // Derived Metrics for display (Fixes zeroed metrics during active experiments)
    const globalStatsArr = Object.values(stats);

    let displayMetrics = {
        total: 0,
        successful: 0,
        successRate: '0%',
        avgDuration: '0s',
        avgTokens: '0k',
        totalLint: 0
    };

    if (globalStatsArr.length > 0) {
        const totalRuns = globalStatsArr.reduce((acc: number, s: any) => acc + (s.count || 0), 0);
        const totalSuccessful = globalStatsArr.reduce((acc: number, s: any) => acc + (s.successCount || 0), 0);
        const totalDurationS = globalStatsArr.reduce((acc: number, s: any) => acc + ((s.avgDuration || 0) * (s.successCount || 0)), 0);
        const totalTokensValue = globalStatsArr.reduce((acc: number, s: any) => acc + ((s.avgTokens || 0) * (s.successCount || 0)), 0);
        const cumulativeLint = globalStatsArr.reduce((acc: number, s: any) => acc + ((s.avgLint || 0) * (s.count || 0)), 0);

        displayMetrics = {
            total: totalRuns,
            successful: totalSuccessful,
            successRate: totalRuns > 0 ? ((totalSuccessful / totalRuns) * 100).toFixed(1) + '%' : '0%',
            avgDuration: totalSuccessful > 0 ? (totalDurationS / totalSuccessful).toFixed(1) + 's' : '0s',
            avgTokens: totalSuccessful > 0 ? (totalTokensValue / totalSuccessful / 1000).toFixed(1) + 'k' : '0k',
            totalLint: Math.round(cumulativeLint)
        };
    }

    return (
        <div className="space-y-6">
            {/* Status Banner */}
            {status === 'failed' && (
                <div className="glass p-6 rounded-2xl border border-red-500/20 bg-red-500/5 transition-all">
                    <h3 className="font-bold flex items-center gap-2 text-red-500 mb-2">
                        <span className="w-2 h-2 rounded-full bg-red-500"></span>
                        Experiment Failed
                    </h3>
                    <p className="text-sm text-red-400 font-mono bg-red-500/10 p-4 rounded-xl border border-red-500/10">
                        {experiment.error_message || "An unknown error occurred during execution."}
                    </p>
                </div>
            )}

            {isActive && (
                <div className={`glass p-6 rounded-2xl border transition-all ${status === 'running' ? 'border-blue-500/20 bg-blue-500/5 animate-pulse' : 'border-amber-500/20 bg-amber-500/5'}`}>
                    <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-4">
                            <h3 className={`font-bold flex items-center gap-2 ${status === 'running' ? 'text-blue-400' : 'text-amber-400'}`}>
                                <span className={`w-2 h-2 rounded-full ${status === 'running' ? 'bg-blue-500 animate-ping' : 'bg-amber-500'}`}></span>
                                {status === 'running' ? 'Experiment in Progress...' : 'Experiment Paused'}
                            </h3>

                            {/* Controls */}
                            <div className="flex gap-2">
                                {status === 'running' ? (
                                    <button
                                        disabled={loadingAction !== null}
                                        onClick={() => handleControl('pause')}
                                        className="bg-amber-500/10 hover:bg-amber-500/20 text-amber-500 text-xs font-bold px-3 py-1 rounded border border-amber-500/20 transition-all uppercase tracking-widest"
                                    >
                                        {loadingAction === 'pause' ? '...' : 'Pause'}
                                    </button>
                                ) : (
                                    <button
                                        disabled={loadingAction !== null}
                                        onClick={() => handleControl('resume')}
                                        className="bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 text-xs font-bold px-3 py-1 rounded border border-emerald-500/20 transition-all uppercase tracking-widest"
                                    >
                                        {loadingAction === 'resume' ? '...' : 'Resume'}
                                    </button>
                                )}
                                <button
                                    disabled={loadingAction !== null}
                                    onClick={() => handleControl('stop')}
                                    className="bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs font-bold px-3 py-1 rounded border border-red-500/20 transition-all uppercase tracking-widest"
                                >
                                    {loadingAction === 'stop' ? '...' : 'Stop'}
                                </button>
                            </div>
                        </div>
                        <span className="text-base font-mono">{checkpoint?.percentage.toFixed(1) || 0}%</span>
                    </div>
                    <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                            className={`h-full transition-all duration-500 ${status === 'running' ? 'bg-blue-500' : 'bg-amber-500'}`}
                            style={{ width: `${checkpoint?.percentage || 0}%` }}
                        ></div>
                    </div>
                    <p className="text-xs text-zinc-500 mt-2 uppercase tracking-widest font-bold">
                        Job {checkpoint?.completed_jobs || 0} of {checkpoint?.total_jobs || 0} completed
                    </p>
                </div>
            )}

            {/* Tabs & Actions */}
            <div className="flex justify-between items-center bg-white/5 p-1 rounded-xl">
                <div className="flex gap-2">
                    <button
                        onClick={() => setTab('analytics')}
                        className={`px-6 py-2 rounded-lg text-base font-bold transition-all ${tab === 'analytics' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-zinc-500 hover:text-white'}`}
                    >
                        Analytics
                    </button>
                    <button
                        onClick={() => setTab('history')}
                        className={`px-6 py-2 rounded-lg text-base font-bold transition-all ${tab === 'history' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-zinc-500 hover:text-white'}`}
                    >
                        Runs History
                    </button>
                    {configContent && (
                        <button
                            onClick={() => setTab('config')}
                            className={`px-6 py-2 rounded-lg text-base font-bold transition-all ${tab === 'config' ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20' : 'text-zinc-500 hover:text-white'}`}
                        >
                            Configuration
                        </button>
                    )}
                </div>

            </div>

            {
                tab === 'analytics' ? (
                    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <p className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-1">Success Rate</p>
                                <p className="text-3xl font-bold text-emerald-400">{displayMetrics.successRate}</p>
                                <p className="text-xs text-zinc-600 mt-1">{displayMetrics.successful} / {displayMetrics.total} Runs Passed</p>
                            </div>
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <p className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-1">Avg Duration</p>
                                <p className="text-3xl font-bold">{displayMetrics.avgDuration}</p>
                                <p className="text-xs text-zinc-600 mt-1">Per Repetition</p>
                            </div>
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <p className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-1">Avg Tokens</p>
                                <p className="text-3xl font-bold text-blue-400">{displayMetrics.avgTokens}</p>
                                <p className="text-xs text-zinc-600 mt-1">Per successful run</p>
                            </div>
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <p className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-1">Lint Issues</p>
                                <p className="text-3xl font-bold text-amber-400">{displayMetrics.totalLint}</p>
                                <p className="text-xs text-zinc-600 mt-1">Cumulative across all runs</p>
                            </div>
                        </div>

                        {/* Performance Analysis Table */}
                        {runResults.length > 0 && (
                            <section className="glass rounded-2xl overflow-hidden border border-white/5">
                                <div className="p-6 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                                    <h3 className="text-lg font-bold">Performance Comparison</h3>
                                    <div className="flex gap-4 text-xs font-bold uppercase tracking-wider text-zinc-500">
                                        <span>* p&lt;0.05</span>
                                        <span>** p&lt;0.01</span>
                                        <span>*** p&lt;0.001</span>
                                    </div>
                                </div>
                                <div className="overflow-x-auto">
                                    <table className="w-full text-left">
                                        <thead>
                                            <tr className="text-zinc-500 text-xs uppercase font-bold tracking-widest border-b border-white/5">
                                                <th className="px-6 py-4">Alternative</th>
                                                <th className="px-6 py-4 text-center">Success Rate</th>
                                                <th className="px-6 py-4 text-right">Avg Duration</th>
                                                <th className="px-6 py-4 text-right">Avg Tokens</th>
                                                <th className="px-6 py-4 text-right">Avg Lint</th>
                                                <th className="px-6 py-4 text-right">Tests Failed</th>
                                            </tr>
                                        </thead>
                                        <tbody className="divide-y divide-white/5">
                                            {altNames.map((alt, idx) => {
                                                const s = stats[alt];

                                                // Calculate significance vs reference (if not reference itself)
                                                let durSig = { level: '', better: false };
                                                let successSig = { level: '', better: false };
                                                let tokenSig = { level: '', better: false };
                                                let lintSig = { level: '', better: false };
                                                let testSig = { level: '', better: false };

                                                if (alt !== referenceAlt) {
                                                    const getLevel = (p: number) => {
                                                        if (p < 0.001) return '***';
                                                        if (p < 0.01) return '**';
                                                        if (p < 0.05) return '*';
                                                        return '';
                                                    };

                                                    // Prefer pre-calculated p-values from DB
                                                    if (s.pDuration !== undefined && s.pDuration !== null) {
                                                        durSig = {
                                                            level: getLevel(s.pDuration),
                                                            better: refStats ? s.avgDuration < refStats.avgDuration : false
                                                        };
                                                    }

                                                    if (s.pSuccess !== undefined && s.pSuccess !== null) {
                                                        successSig = {
                                                            level: getLevel(s.pSuccess),
                                                            better: refStats ? s.successRate > refStats.successRate : false
                                                        };
                                                    }

                                                    if (s.pTokens !== undefined && s.pTokens !== null) {
                                                        tokenSig = {
                                                            level: getLevel(s.pTokens),
                                                            better: refStats ? s.avgTokens < refStats.avgTokens : false
                                                        };
                                                    }

                                                    if (s.pLint !== undefined && s.pLint !== null) {
                                                        lintSig = {
                                                            level: getLevel(s.pLint),
                                                            better: refStats ? s.avgLint < refStats.avgLint : false
                                                        };
                                                    }

                                                    if (s.pTestsFailed !== undefined && s.pTestsFailed !== null) {
                                                        testSig = {
                                                            level: getLevel(s.pTestsFailed),
                                                            better: refStats ? s.avgTestsFailed < refStats.avgTestsFailed : false
                                                        };
                                                    }
                                                }

                                                return (
                                                    <tr
                                                        key={idx}
                                                        onClick={() => {
                                                            setSelectedAlternative(alt);
                                                            setTab('history');
                                                        }}
                                                        className={`group hover:bg-white/[0.04] cursor-pointer transition-colors ${alt === selectedAlternative ? 'bg-blue-500/10 border-l-4 border-l-blue-500' : alt === referenceAlt ? 'bg-blue-500/5' : ''}`}
                                                    >
                                                        <td className="px-6 py-4 font-bold text-base text-gray-200">
                                                            {alt}
                                                            {alt === referenceAlt && <span className="ml-2 text-[8px] uppercase bg-blue-500 text-white px-1.5 py-0.5 rounded tracking-widest">Ref</span>}
                                                        </td>
                                                        <td className="px-6 py-4 text-center">
                                                            <div className="flex items-center justify-center gap-1">
                                                                <span className={`font-mono font-bold ${s.successRate >= 90 ? 'text-emerald-400' : s.successRate >= 70 ? 'text-amber-400' : 'text-red-400'
                                                                    }`}>
                                                                    {s.successRate.toFixed(1)}%
                                                                </span>
                                                                {successSig.level && (
                                                                    <span className="text-sm text-blue-400 font-bold" title="Statistically Significant">{successSig.level}</span>
                                                                )}
                                                            </div>
                                                            <div className="text-xs text-zinc-600 mt-0.5">{s.successCount}/{s.count} runs</div>
                                                        </td>
                                                        <td className="px-6 py-4 text-right font-mono text-zinc-300">
                                                            {s.avgDuration.toFixed(2)}s
                                                            {durSig.level && (
                                                                <sup className={`ml-1 font-bold ${durSig.better ? 'text-emerald-400' : 'text-red-400'}`}>{durSig.level}</sup>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4 text-right font-mono text-zinc-400">
                                                            {(s.avgTokens / 1000).toFixed(1)}k
                                                            {tokenSig.level && (
                                                                <sup className={`ml-0.5 font-bold ${tokenSig.better ? 'text-emerald-400' : 'text-red-400'}`}>{tokenSig.level}</sup>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className={`font-mono ${s.avgLint > 0 ? 'text-amber-400' : 'text-emerald-400'}`}>
                                                                {s.avgLint.toFixed(1)}
                                                            </span>
                                                            {lintSig.level && (
                                                                <sup className={`ml-0.5 font-bold ${lintSig.better ? 'text-emerald-400' : 'text-red-400'}`}>{lintSig.level}</sup>
                                                            )}
                                                        </td>
                                                        <td className="px-6 py-4 text-right">
                                                            <span className={`font-mono ${s.avgTestsFailed > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                                                                {s.avgTestsFailed?.toFixed(1) || '0.0'}
                                                            </span>
                                                            {testSig.level && (
                                                                <sup className={`ml-0.5 font-bold ${testSig.better ? 'text-emerald-400' : 'text-red-400'}`}>{testSig.level}</sup>
                                                            )}
                                                        </td>
                                                    </tr>
                                                );
                                            })}
                                        </tbody>
                                    </table>
                                </div>
                            </section>
                        )}

                        {/* Config Summary */}
                        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-4">Alternatives</h3>
                                <div className="space-y-3">
                                    {config?.alternatives
                                        ?.map((alt: any, idx: number) => (
                                            <div key={idx} className="flex justify-between items-center group">
                                                <span className={`text-base font-bold ${alt.name === referenceAlt ? 'text-blue-400' : 'text-gray-300'}`}>
                                                    {alt.name} {alt.name === referenceAlt && <span className="text-[10px] bg-blue-500/20 text-blue-300 px-1.5 rounded ml-2">REF</span>}
                                                </span>
                                                <span className="text-sm text-zinc-500 font-mono">{alt.model}</span>
                                            </div>
                                        ))}
                                    {config?.alternatives?.filter((alt: any) => altNames.includes(alt.name)).length === 0 && (
                                        <p className="text-zinc-500 text-sm italic">No alternatives run.</p>
                                    )}
                                </div>
                            </div>
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-4">Scenarios</h3>
                                <div className="flex flex-wrap gap-2">
                                    {config?.scenarios
                                        ?.map((scen: any, idx: number) => (
                                            <span key={idx} className="px-2.5 py-1 rounded-md bg-white/5 text-sm font-medium text-gray-300 border border-white/5">
                                                {scen.name}
                                            </span>
                                        ))}
                                    {config?.scenarios?.filter((scen: any) => runResults.some(r => r.scenario === scen.name)).length === 0 && (
                                        <p className="text-zinc-500 text-sm italic">No scenarios run.</p>
                                    )}
                                </div>
                            </div>
                            <div className="glass p-6 rounded-2xl border border-white/5">
                                <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest mb-4">Parameters</h3>
                                <div className="space-y-2 text-base">
                                    <div className="flex justify-between items-center">
                                        <span className="text-zinc-500">Repetitions</span>
                                        <span className="font-bold text-gray-200">{experiment.reps}</span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-zinc-500">Concurrent</span>
                                        <span className="font-bold text-gray-200">{experiment.concurrent}</span>
                                    </div>
                                    <div className="mt-4 flex flex-col gap-2">
                                        <button
                                            onClick={handleExplain}
                                            disabled={loadingAction === 'explain'}
                                            className="w-full py-2 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 font-bold rounded-xl border border-blue-500/20 transition-all text-xs uppercase tracking-widest disabled:opacity-50"
                                        >
                                            {loadingAction === 'explain' ? 'Consulting Gemini...' : '✨ Generate AI Insights'}
                                        </button>
                                        <button
                                            onClick={handleRegenerate}
                                            disabled={!!loadingAction}
                                            className="w-full py-2 bg-white/5 hover:bg-white/10 text-zinc-400 font-bold rounded-xl border border-white/5 transition-all text-xs uppercase tracking-widest disabled:opacity-50"
                                        >
                                            {loadingAction === 'regenerate' ? 'Analyzing...' : 'Re-analyze Results'}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </section>

                        {/* AI Insights Section */}
                        {aiAnalysis && (
                            <section className="glass p-8 rounded-2xl border border-blue-500/20 bg-blue-500/[0.02] animate-in fade-in slide-in-from-top-4 duration-500">
                                <div className="flex items-center gap-3 mb-6">
                                    <span className="text-2xl">✨</span>
                                    <h3 className="text-lg font-bold text-blue-400 uppercase tracking-widest">AI Deep-Dive Insights</h3>
                                </div>
                                <div className="prose prose-invert prose-blue max-w-none prose-p:leading-relaxed prose-p:text-zinc-300">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                        {aiAnalysis}
                                    </ReactMarkdown>
                                </div>
                            </section>
                        )}

                        {/* Failure Analysis Section */}
                        {runResults.some(r => !r.is_success) && (
                            <section className="glass p-8 rounded-2xl border border-red-500/20 bg-red-500/[0.01]">
                                <div className="flex items-center gap-3 mb-6">
                                    <span className="text-2xl">🚨</span>
                                    <h3 className="text-lg font-bold text-red-500 uppercase tracking-widest">Failure Patterns Analysis</h3>
                                </div>

                                <div className="space-y-8">
                                    {/* Grouped Failures */}
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                                        <div>
                                            <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                                                <span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Primary Failure modes
                                            </h4>
                                            <div className="space-y-3">
                                                {(() => {
                                                    const groups: Record<string, { count: number; alts: Set<string> }> = {};
                                                    runResults.filter(r => !r.is_success).forEach(r => {
                                                        let reason = r.error || "Validation Failure";
                                                        if (reason.includes("timeout")) reason = "Experiment Timeout";
                                                        if (!groups[reason]) groups[reason] = { count: 0, alts: new Set() };
                                                        groups[reason].count++;
                                                        groups[reason].alts.add(r.alternative);
                                                    });
                                                    return Object.entries(groups).map(([reason, data], i) => (
                                                        <div key={i} className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                                                            <div className="flex justify-between items-start mb-2">
                                                                <span className="text-sm font-bold text-zinc-300">{reason}</span>
                                                                <span className="text-xs font-black text-red-500 bg-red-500/10 px-2 py-0.5 rounded">{data.count} runs</span>
                                                            </div>
                                                            <div className="flex flex-wrap gap-1">
                                                                {Array.from(data.alts).map(alt => (
                                                                    <span key={alt} className="text-[10px] text-zinc-500 px-1.5 py-0.5 bg-white/5 rounded lowercase">{alt}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ));
                                                })()}
                                            </div>
                                        </div>

                                        <div>
                                            <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-widest mb-4 flex items-center gap-2">
                                                <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span> Critical Quality Issues
                                            </h4>
                                            <div className="space-y-3">
                                                {(() => {
                                                    const lintIssues: Record<string, { count: number; alts: Set<string> }> = {};
                                                    runResults.filter(r => r.lint_issues > 0).forEach(r => {
                                                        // This only counts at high level since we don't have individual lint messages here
                                                        // but we can at least show which alts struggle most
                                                        const message = "Lint/Style Violations";
                                                        if (!lintIssues[message]) lintIssues[message] = { count: 0, alts: new Set() };
                                                        lintIssues[message].count += 1;
                                                        lintIssues[message].alts.add(r.alternative);
                                                    });

                                                    return Object.entries(lintIssues).map(([reason, data], i) => (
                                                        <div key={i} className="p-4 rounded-xl bg-white/[0.02] border border-white/5">
                                                            <div className="flex justify-between items-start mb-2">
                                                                <span className="text-sm font-bold text-amber-500/80">{reason}</span>
                                                                <span className="text-xs font-black text-amber-500 bg-amber-500/10 px-2 py-0.5 rounded">{data.count} runs</span>
                                                            </div>
                                                            <div className="flex flex-wrap gap-1">
                                                                {Array.from(data.alts).map(alt => (
                                                                    <span key={alt} className="text-[10px] text-zinc-500 px-1.5 py-0.5 bg-white/5 rounded lowercase">{alt}</span>
                                                                ))}
                                                            </div>
                                                        </div>
                                                    ));
                                                })()}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        )}

                        {/* Markdown Report Content */}
                        {initialContent && (
                            <section className="glass p-8 rounded-2xl border border-white/5 prose prose-invert prose-emerald max-w-none prose-pre:bg-black/40 prose-pre:border prose-pre:border-white/5">
                                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                    {initialContent}
                                </ReactMarkdown>
                            </section>
                        )}
                    </div>
                ) : tab === 'config' ? (
                    <div className="space-y-6 animate-in fade-in duration-500">
                        <div className="glass p-6 rounded-2xl border border-white/5 bg-black/40">
                            <div className="flex justify-between items-center mb-4">
                                <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest">Experiment Definition</h3>
                                <span className="text-xs text-zinc-600 font-mono">config.yaml</span>
                            </div>
                            <pre className="text-sm font-mono text-zinc-300 leading-relaxed overflow-x-auto whitespace-pre-wrap">
                                {configContent}
                            </pre>
                        </div>
                    </div>
                ) : (
                    <div className="space-y-6 animate-in fade-in duration-500">
                        {/* Configuration Diff (Only if an alternative is selected) */}
                        {selectedAlternative && config && (
                            <div className="glass rounded-2xl border border-blue-500/20 bg-blue-500/5 p-6 animate-in zoom-in-95 duration-300">
                                <div className="flex justify-between items-center mb-6">
                                    <h3 className="text-xl font-bold flex items-center gap-2">
                                        <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                                        Configuration Diff: {selectedAlternative}
                                    </h3>
                                    <button
                                        onClick={() => setSelectedAlternative(null)}
                                        className="text-xs font-bold text-blue-400 hover:text-blue-300 uppercase tracking-widest flex items-center gap-1 transition-colors"
                                    >
                                        Clear Selection ✕
                                    </button>
                                </div>

                                <ConfigDiffView
                                    selectedAlt={config.alternatives.find((a: any) => a.name === selectedAlternative)}
                                    controlAlt={config.alternatives.find((a: any) => a.name === (experiment.experiment_control || config.control || config.alternatives[0].name))}
                                    fileContents={fileContents}
                                    loadingFiles={loadingFiles}
                                />
                            </div>
                        )}

                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                            <div className="lg:col-span-4 space-y-4">
                                <div className="flex justify-between items-center px-2">
                                    <h3 className="text-sm font-bold text-zinc-500 uppercase tracking-widest">Repetitions</h3>
                                    {selectedAlternative && (
                                        <button
                                            onClick={() => setSelectedAlternative(null)}
                                            className="text-[10px] font-bold text-blue-400 hover:text-blue-300 uppercase tracking-widest flex items-center gap-1 transition-colors"
                                        >
                                            Clear Filter: {selectedAlternative} ✕
                                        </button>
                                    )}
                                </div>
                                <div className="glass rounded-2xl border border-white/5 overflow-hidden divide-y divide-white/5">
                                    {runResults
                                        .filter(r => !selectedAlternative || r.alternative === selectedAlternative)
                                        .map((run, i) => (
                                            <button
                                                key={i}
                                                onClick={() => fetchRunDetails(run)}
                                                className={`w-full p-4 text-left transition-all hover:bg-white/5 ${selectedRun?.id === run.id ? 'bg-blue-600/10 border-l-4 border-l-blue-500' : ''}`}
                                            >
                                                <div className="flex justify-between items-start">
                                                    <div>
                                                        <p className="font-bold text-sm text-gray-200">{run.alternative}</p>
                                                        <p className="text-xs text-zinc-500 mt-0.5 uppercase tracking-tighter">{run.scenario}</p>
                                                    </div>
                                                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-widest ${run.status === 'SUCCESS' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                                                        {run.status}
                                                    </span>
                                                </div>
                                                <div className="flex gap-4 mt-3 text-[10px] items-center text-zinc-500 font-mono">
                                                    <span title="Tokens">🪙 {(run.total_tokens / 1000).toFixed(1)}k</span>
                                                    <span title="Tools">🛠️ {run.tool_calls_count}</span>
                                                    <span title="Duration">⏱️ {(run.duration / 1e9).toFixed(1)}s</span>
                                                </div>
                                            </button>
                                        ))}
                                </div>
                            </div>

                            {/* Run Details */}
                            <div className="lg:col-span-8 space-y-6">
                                {!selectedRun ? (
                                    <div className="glass h-[600px] rounded-2xl border border-white/5 flex flex-col items-center justify-center text-zinc-500 space-y-4">
                                        <span className="text-4xl">🔬</span>
                                        <p className="font-bold uppercase tracking-widest text-sm">Select a run to view details</p>
                                    </div>
                                ) : loadingDetails ? (
                                    <div className="glass h-[600px] rounded-2xl border border-white/5 flex flex-col items-center justify-center text-zinc-500 animate-pulse">
                                        <p className="font-bold uppercase tracking-widest text-sm">Hypothesizing data...</p>
                                    </div>
                                ) : (
                                    <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-500">
                                        {/* Run Header Stats */}
                                        <div className="grid grid-cols-4 gap-4">
                                            <div className="glass p-4 rounded-xl border border-white/5">
                                                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Tokens</p>
                                                <p className="text-xl font-bold">{selectedRun.total_tokens?.toLocaleString()}</p>
                                                <p className="text-[9px] text-zinc-600 mt-1 uppercase">In_{selectedRun.input_tokens} Out_{selectedRun.output_tokens}</p>
                                            </div>
                                            <div className="glass p-4 rounded-xl border border-white/5">
                                                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Tools</p>
                                                <p className="text-xl font-bold">{selectedRun.tool_calls_count}</p>
                                            </div>
                                            <div className="glass p-4 rounded-xl border border-white/5">
                                                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Tests</p>
                                                <p className="text-xl font-bold text-emerald-400">{selectedRun.tests_passed}</p>
                                                <p className="text-[9px] text-red-500 mt-1 uppercase">{selectedRun.tests_failed} Failures</p>
                                            </div>
                                            <div className="glass p-4 rounded-xl border border-white/5">
                                                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1">Lint</p>
                                                <p className="text-xl font-bold text-amber-400">{selectedRun.lint_issues}</p>
                                            </div>
                                        </div>

                                        {/* Validation Report */}
                                        {selectedRun.validation_report && (() => {
                                            try {
                                                const report = JSON.parse(selectedRun.validation_report);
                                                return (
                                                    <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                        <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                                                            <h4 className="text-sm font-bold uppercase tracking-widest text-blue-400">Validation Report</h4>
                                                            <div className="flex gap-4">
                                                                <span className={`text-[10px] font-bold uppercase tracking-widest ${report.overall_success ? 'text-emerald-400' : 'text-red-500'}`}>
                                                                    {report.overall_success ? 'Passed' : 'Failed'}
                                                                </span>
                                                                <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Score: {report.total_score}</span>
                                                            </div>
                                                        </div>
                                                        <div className="overflow-x-auto">
                                                            <table className="w-full text-left text-xs">
                                                                <thead className="text-zinc-500 uppercase font-bold tracking-widest bg-white/[0.01]">
                                                                    <tr>
                                                                        <th className="px-4 py-3">Type</th>
                                                                        <th className="px-4 py-3">Description</th>
                                                                        <th className="px-4 py-3 text-right">Status</th>
                                                                    </tr>
                                                                </thead>
                                                                <tbody className="divide-y divide-white/5">
                                                                    {report.items.map((item: any, i: number) => (
                                                                        <tr key={i} className="hover:bg-white/[0.04] active:bg-white/[0.06] group cursor-pointer transition-colors" onClick={() => setInspectingValidation(item)}>
                                                                            <td className="px-4 py-3 font-mono text-zinc-400 uppercase">{item.type}</td>
                                                                            <td className="px-4 py-3">
                                                                                <p className="font-bold text-gray-300">{item.description}</p>
                                                                                {item.details && (
                                                                                    <p className="text-[10px] text-zinc-500 truncate max-w-md">{item.details.split('\n')[0]}</p>
                                                                                )}
                                                                            </td>
                                                                            <td className="px-4 py-3 text-right">
                                                                                <div className="flex items-center justify-end gap-3">
                                                                                    <span className={`font-bold ${item.status === 'PASS' ? 'text-emerald-400' : 'text-red-500'}`}>{item.status}</span>
                                                                                    <button className="text-[10px] uppercase text-blue-500 font-bold opacity-0 group-hover:opacity-100 transition-opacity">Details</button>
                                                                                </div>
                                                                            </td>
                                                                        </tr>
                                                                    ))}
                                                                </tbody>
                                                            </table>
                                                        </div>
                                                    </div>
                                                );
                                            } catch (e) {
                                                return null;
                                            }
                                        })()}

                                        {/* Thread View */}
                                        <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                            <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                                                <h4 className="text-sm font-bold uppercase tracking-widest">Conversation Thread</h4>
                                            </div>
                                            <div className="p-6 space-y-6 max-h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-800">
                                                {runDetails?.messages.length === 0 && runDetails?.tools.length === 0 && (
                                                    <p className="text-zinc-500 italic text-sm text-center py-10">No thread data available for this run.</p>
                                                )}
                                                {runDetails?.messages.map((msg, i) => (
                                                    <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                                                        <span className="text-[10px] font-bold text-zinc-600 uppercase tracking-tighter mb-1 ml-1">{msg.role}</span>
                                                        <div className={`p-4 rounded-2xl text-sm max-w-[85%] ${msg.role === 'user' ? 'bg-blue-600/20 text-blue-100' : 'bg-white/5 text-gray-200 shadow-xl'}`}>
                                                            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                                                                {msg.content}
                                                            </ReactMarkdown>
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        </div>

                                        {/* Tool Usage */}
                                        {runDetails?.tools && runDetails.tools.length > 0 && (
                                            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                                                    <h4 className="text-sm font-bold uppercase tracking-widest text-amber-500">Tool Executions</h4>
                                                </div>
                                                <div className="overflow-x-auto">
                                                    <table className="w-full text-left text-xs">
                                                        <thead className="text-zinc-500 uppercase font-bold tracking-widest bg-white/[0.01]">
                                                            <tr>
                                                                <th className="px-4 py-3">Tool</th>
                                                                <th className="px-4 py-3">Status</th>
                                                                <th className="px-4 py-3">Duration</th>
                                                                <th className="px-4 py-3 text-right">Details</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5">
                                                            {runDetails?.tools?.map((tool, i) => (
                                                                <tr key={i} className="hover:bg-white/[0.01]">
                                                                    <td className="px-4 py-3 font-mono font-bold text-blue-400">{tool.name}</td>
                                                                    <td className="px-4 py-3">
                                                                        <span className={tool.status === 'success' ? 'text-emerald-400' : 'text-red-400'}>{tool.status}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-zinc-500 font-mono">{tool.duration.toFixed(3)}s</td>
                                                                    <td className="px-4 py-3 text-right">
                                                                        <button onClick={() => setInspectingTool(tool)} className="text-[10px] uppercase text-blue-500 hover:text-blue-400 font-bold transition-colors">Inspect</button>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        )}
                                        {/* Test Results */}
                                        {runDetails?.tests && runDetails.tests.length > 0 && (
                                            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                                                    <h4 className="text-sm font-bold uppercase tracking-widest text-emerald-500">Test Outcomes</h4>
                                                    <div className="flex gap-4">
                                                        <span className="text-[10px] text-emerald-400 font-bold uppercase tracking-widest">{runDetails?.tests?.filter((t: any) => t.status === 'PASS').length} Passed</span>
                                                        <span className="text-[10px] text-red-500 font-bold uppercase tracking-widest">{runDetails?.tests?.filter((t: any) => t.status === 'FAIL').length} Failed</span>
                                                    </div>
                                                </div>
                                                <div className="overflow-x-auto max-h-[400px]">
                                                    <table className="w-full text-left text-xs">
                                                        <thead className="text-zinc-500 uppercase font-bold tracking-widest bg-white/[0.01]">
                                                            <tr>
                                                                <th className="px-4 py-3">Test Name</th>
                                                                <th className="px-4 py-3">Status</th>
                                                                <th className="px-4 py-3 text-right">Duration</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5">
                                                            {runDetails?.tests?.map((test: any, i: number) => (
                                                                <tr key={i} className="hover:bg-white/[0.01] group">
                                                                    <td className="px-4 py-3 font-mono">
                                                                        <p className="font-bold text-gray-300">{test.name}</p>
                                                                        {test.status === 'FAIL' && test.output && (
                                                                            <pre className="mt-2 text-[10px] text-red-400 bg-red-400/5 p-2 rounded overflow-x-auto whitespace-pre-wrap font-mono leading-relaxed max-h-[200px]">{test.output}</pre>
                                                                        )}
                                                                    </td>
                                                                    <td className="px-4 py-3">
                                                                        <span className={`font-bold ${test.status === 'PASS' ? 'text-emerald-400' : 'text-red-500'}`}>{test.status}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-right text-zinc-500">{(test.duration_ns / 1e6).toFixed(1)}ms</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        )}

                                        {/* Lint Findings */}
                                        {runDetails?.lints && runDetails.lints.length > 0 && (
                                            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                                                    <h4 className="text-sm font-bold uppercase tracking-widest text-amber-500">Lint Findings</h4>
                                                </div>
                                                <div className="overflow-x-auto max-h-[400px]">
                                                    <table className="w-full text-left text-xs">
                                                        <thead className="text-zinc-500 uppercase font-bold tracking-widest bg-white/[0.01]">
                                                            <tr>
                                                                <th className="px-4 py-3">Location</th>
                                                                <th className="px-4 py-3">Message</th>
                                                                <th className="px-4 py-3 text-right">Rule</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-white/5">
                                                            {runDetails?.lints?.map((lint: any, i: number) => (
                                                                <tr key={i} className="hover:bg-white/[0.01]">
                                                                    <td className="px-4 py-3 font-mono text-zinc-400 min-w-[200px]">
                                                                        {lint.file}:{lint.line}:{lint.col}
                                                                    </td>
                                                                    <td className="px-4 py-3 text-gray-300">{lint.message}</td>
                                                                    <td className="px-4 py-3 text-right font-mono text-amber-400/80">{lint.rule_id}</td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            </div>
                                        )}

                                        {runDetails?.files && runDetails.files.length > 0 && (
                                            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                <div className="p-4 border-b border-white/5 bg-white/[0.02] flex justify-between items-center">
                                                    <h4 className="text-sm font-bold uppercase tracking-widest text-emerald-500">Workspace Snapshot</h4>
                                                    <span className="text-[10px] text-zinc-500 font-mono uppercase italic">Captured from DB</span>
                                                </div>
                                                <div className="grid grid-cols-12 h-[400px]">
                                                    <div className="col-span-4 border-r border-white/5 overflow-y-auto bg-black/20">
                                                        {runDetails.files.map((file, i) => (
                                                            <button
                                                                key={i}
                                                                onClick={() => setSelectedFile(file)}
                                                                className={`w-full p-3 text-left text-xs font-mono border-b border-white/5 transition-all hover:bg-white/5 ${selectedFile?.id === file.id ? 'bg-emerald-500/10 text-emerald-400 border-l-2 border-l-emerald-500' : 'text-zinc-400'}`}
                                                            >
                                                                {file.path}
                                                            </button>
                                                        ))}
                                                    </div>
                                                    <div className="col-span-8 overflow-y-auto bg-black/40 p-4">
                                                        {selectedFile ? (
                                                            <pre className="text-[11px] font-mono text-zinc-300 whitespace-pre-wrap">{selectedFile.content}</pre>
                                                        ) : (
                                                            <p className="text-zinc-600 italic text-center text-xs mt-20 uppercase font-bold tracking-tighter">Select a file to view content</p>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        {/* Run Errors & Logs */}
                                        {(selectedRun.error || selectedRun.stdout || selectedRun.stderr) && (
                                            <div className="glass rounded-2xl border border-white/5 overflow-hidden">
                                                <div className="p-4 border-b border-white/5 bg-white/[0.02]">
                                                    <h4 className="text-sm font-bold uppercase tracking-widest text-zinc-500">Execution Details & Logs</h4>
                                                </div>
                                                <div className="p-4 bg-black/40 font-mono text-[10px] space-y-4 max-h-[400px] overflow-y-auto">
                                                    {selectedRun.error && (
                                                        <div className="space-y-1">
                                                            <p className="text-red-500 uppercase font-black tracking-widest">--- Failure Reason ---</p>
                                                            <pre className="text-red-400 bg-red-400/10 p-4 rounded-lg border border-red-500/20 whitespace-pre-wrap text-xs">{selectedRun.error}</pre>
                                                        </div>
                                                    )}
                                                    {selectedRun.stdout && (
                                                        <div className="space-y-1">
                                                            <p className="text-blue-500/50 uppercase font-bold">--- stdout ---</p>
                                                            <pre className="text-zinc-400 whitespace-pre-wrap">{selectedRun.stdout}</pre>
                                                        </div>
                                                    )}
                                                    {selectedRun.stderr && (
                                                        <div className="space-y-1">
                                                            <p className="text-red-500/50 uppercase font-bold">--- stderr ---</p>
                                                            <pre className="text-red-400/80 whitespace-pre-wrap">{selectedRun.stderr}</pre>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )
            }

            {/* Tool Inspection Modal */}
            {
                inspectingTool && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
                        <div className="glass w-full max-w-4xl max-h-[90vh] rounded-3xl border border-white/10 shadow-2xl flex flex-col overflow-hidden text-left">
                            <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                                <div>
                                    <h3 className="text-xl font-bold text-blue-400 font-mono flex items-center gap-2">
                                        <span className="text-zinc-500 text-sm">tool:</span> {inspectingTool.name}
                                    </h3>
                                    <p className="text-[10px] text-zinc-500 mt-1 uppercase tracking-widest font-bold">
                                        Executed in {inspectingTool.duration.toFixed(3)}s • {new Date(inspectingTool.timestamp).toLocaleTimeString()}
                                    </p>
                                </div>
                                <button
                                    onClick={() => setInspectingTool(null)}
                                    className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-zinc-400 hover:text-white transition-all text-xl"
                                >
                                    ✕
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-8 space-y-8 scrollbar-thin scrollbar-thumb-zinc-800">
                                <section className="space-y-3">
                                    <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
                                        <span className="w-1 h-1 rounded-full bg-blue-500"></span> Arguments
                                    </h4>
                                    <pre className="p-4 rounded-xl bg-black/40 border border-white/5 text-xs text-blue-300 whitespace-pre-wrap font-mono leading-relaxed">
                                        {inspectingTool.args ? JSON.stringify(JSON.parse(inspectingTool.args), null, 2) : "No arguments"}
                                    </pre>
                                </section>

                                <section className="space-y-3">
                                    <h4 className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest flex items-center gap-2">
                                        <span className={`w-1 h-1 rounded-full ${inspectingTool.status === 'success' ? 'bg-emerald-500' : 'bg-red-500'}`}></span>
                                        {inspectingTool.status === 'success' ? 'Output' : 'Error Response'}
                                    </h4>
                                    <pre className={`p-4 rounded-xl border text-xs whitespace-pre-wrap font-mono leading-relaxed ${inspectingTool.status === 'success' ? 'bg-black/40 border-white/5 text-zinc-300' : 'bg-red-500/5 border-red-500/20 text-red-400'
                                        }`}>
                                        {inspectingTool.status === 'success' ? inspectingTool.output : inspectingTool.error || inspectingTool.output}
                                    </pre>
                                </section>
                            </div>

                            <div className="p-4 border-t border-white/5 bg-white/[0.01] flex justify-end">
                                <button
                                    onClick={() => setInspectingTool(null)}
                                    className="px-6 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-bold transition-all text-white"
                                >
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
            {/* Validation Inspection Modal */}
            {
                inspectingValidation && (
                    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 animate-in fade-in duration-300">
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setInspectingValidation(null)} />
                        <div className="glass w-full max-w-4xl max-h-[80vh] rounded-3xl border border-white/10 shadow-2xl relative overflow-hidden flex flex-col">
                            <div className="p-6 border-b border-white/5 flex justify-between items-center bg-white/[0.02]">
                                <div>
                                    <span className="text-[10px] font-bold text-blue-500 uppercase tracking-widest block mb-1">{inspectingValidation.type} Validation</span>
                                    <h3 className="text-xl font-bold">{inspectingValidation.description}</h3>
                                </div>
                                <button onClick={() => setInspectingValidation(null)} className="text-zinc-500 hover:text-white transition-colors">
                                    <span className="sr-only">Close</span>
                                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                </button>
                            </div>
                            <div className="p-8 overflow-y-auto scrollbar-thin scrollbar-thumb-zinc-800">
                                <div className="flex items-center gap-4 mb-6">
                                    <span className={`px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-widest ${inspectingValidation.status === 'PASS' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                                        {inspectingValidation.status}
                                    </span>
                                    {inspectingValidation.score !== undefined && (
                                        <span className="text-sm text-zinc-400 font-bold uppercase tracking-widest">Score: {inspectingValidation.score}</span>
                                    )}
                                </div>
                                <div className="space-y-4">
                                    <h4 className="text-xs font-bold text-zinc-500 uppercase tracking-widest">Output / Details</h4>
                                    <pre className="bg-black/50 p-6 rounded-2xl border border-white/5 text-sm font-mono text-zinc-300 whitespace-pre-wrap leading-relaxed">
                                        {inspectingValidation.details || "No additional details available."}
                                    </pre>
                                </div>
                            </div>
                        </div>
                    </div>
                )
            }
        </div >
    );
}
