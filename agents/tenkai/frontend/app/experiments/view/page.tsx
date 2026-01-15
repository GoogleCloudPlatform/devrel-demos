"use client";

import React, { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import yaml from "js-yaml";
import { getSimplifiedMetrics, getCheckpoint, getRunResults, getExperimentSummaries, getExperiment, ExperimentRecord, ExperimentSummaryRow, RunResultRecord, Checkpoint } from "@/app/api/api";
import ReportViewer from "@/components/ReportViewer";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ChevronLeft, Loader2 } from "lucide-react";

function ExperimentViewContent() {
    const searchParams = useSearchParams();
    const id = searchParams.get('id');

    const [experiment, setExperiment] = useState<ExperimentRecord | null>(null);
    const [summaries, setSummaries] = useState<ExperimentSummaryRow[]>([]);
    const [runs, setRuns] = useState<RunResultRecord[]>([]);
    const [metrics, setMetrics] = useState<any>(null);
    const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!id) return;

        setLoading(true);
        Promise.all([
            getExperiment(id),
            getExperimentSummaries(id),
            getRunResults(id),
            getSimplifiedMetrics(id).catch(() => null),
            getCheckpoint(id).catch(() => null)
        ]).then(([expData, sumData, runsData, metricsData, checkData]) => {
            setExperiment(expData);
            setSummaries(sumData);
            setRuns(runsData);
            setMetrics(metricsData);
            setCheckpoint(checkData);
        }).catch(err => {
            console.error(err);
            setError("Failed to load experiment data.");
        }).finally(() => {
            setLoading(false);
        });
    }, [id]);

    if (!id) return <div className="p-8 text-center">Missing Experiment ID</div>;
    if (loading) return <div className="flex bg-[#09090b] h-screen items-center justify-center"><Loader2 className="animate-spin text-white" /></div>;
    if (error || !experiment) return <div className="p-8 text-center text-red-500">{error || "Experiment not found"}</div>;

    let configYaml: any = null;
    try { if (experiment.config_content) configYaml = yaml.load(experiment.config_content); } catch (e) { }

    const statObj: any = {};
    summaries.forEach(row => {
        statObj[row.alternative] = { ...row, alternative: row.alternative, count: row.total_runs };
    });

    return (
        <div className="flex h-screen overflow-hidden bg-[#09090b] text-zinc-300">
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
                <header className="border-b border-[#27272a] bg-[#09090b] px-6 py-4 flex items-center justify-between shrink-0">
                    <div className="flex items-center gap-4">
                        <Link href="/experiments">
                            <Button variant="ghost" size="icon">
                                <ChevronLeft className="h-5 w-5" />
                            </Button>
                        </Link>
                        <div>
                            <div className="flex items-center gap-3">
                                <h1 className="text-xl font-bold text-white">{experiment.name}</h1>
                                <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${experiment.status === 'RUNNING' ? 'bg-blue-500/10 text-blue-500 animate-pulse' :
                                        experiment.status === 'COMPLETED' ? 'bg-green-500/10 text-green-500' :
                                            'bg-zinc-800 text-zinc-400'
                                    }`}>
                                    {experiment.status}
                                </span>
                            </div>
                            <p className="text-sm text-zinc-500 mt-0.5 flex items-center gap-2">
                                ID: {experiment.id} • {new Date(experiment.timestamp).toLocaleString()}
                            </p>
                        </div>
                    </div>
                    <RefreshOnInterval active={experiment.status === 'RUNNING'} />
                </header>

                <main className="flex-1 overflow-auto p-0">
                    <ReportViewer
                        experiment={experiment}
                        initialContent={experiment.report_content || ""} // Pass as initialContent
                        initialMetrics={metrics}
                        initialCheckpoint={checkpoint}
                        runResults={runs}
                        stats={statObj}
                        config={configYaml}
                        configContent={experiment.config_content || ""}
                    />
                </main>
            </div>
        </div>
    );
}

export default function ExperimentViewPage() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center bg-[#09090b]"><Loader2 className="animate-spin text-white" /></div>}>
            <ExperimentViewContent />
        </Suspense>
    );
}
