"use client";

import React, { Suspense, useState, useEffect } from "react";
import yaml from "js-yaml";
import { getSimplifiedMetrics, getCheckpoint, getRunResults, getExperimentSummaries, getExperiment, getBlocks } from "@/lib/api";
import ReportViewer from "@/components/ReportViewer";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import Link from "next/link";
import ExperimentSidebar from "@/components/experiments/ExperimentSidebar";
import { Loader2 } from "lucide-react";

function ReportPageContent({ id }: { id: string }) {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<any>(null);

    useEffect(() => {
        if (!id) return;

        const fetchData = async () => {
            try {
                // Fetch basic experiment data first to handle 404 quickly
                let experiment;
                try {
                    experiment = await getExperiment(parseInt(id));
                } catch (e: any) {
                    if (e.message && e.message.includes("404")) {
                        setError('404');
                    } else {
                        console.error(e);
                        setError('CONNECTION_FAILED');
                    }
                    setLoading(false);
                    return;
                }

                if (!experiment) {
                    setError('404');
                    setLoading(false);
                    return;
                }

                const [metrics, checkpoint, runResults, summaries, blocks] = await Promise.all([
                    getSimplifiedMetrics(experiment.id),
                    getCheckpoint(String(experiment.id)),
                    getRunResults(String(experiment.id), 1, 5000),
                    getExperimentSummaries(experiment.id),
                    getBlocks()
                ]);

                setData({ experiment, metrics, checkpoint, runResults, summaries, blocks });
                setLoading(false);
            } catch (e) {
                console.error(e);
                setError('SYNC_FAILED');
                setLoading(false);
            }
        };

        fetchData();
    }, [id]);

    if (loading) {
        return <div className="p-10 text-center opacity-50"><Loader2 className="animate-spin inline mr-2" />Loading Report...</div>;
    }

    if (error === 'CONNECTION_FAILED') {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-red-500">Connection Failed</h1>
                <p className="text-body mb-8">Could not connect to the Tenkai backend.</p>
                <p className="text-zinc-500 text-sm mb-8 font-mono">Ensure 'tenkai --serve' is running.</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }

    if (error === '404') {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-red-500">404</h1>
                <p className="text-body mb-8">Study Purged</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }

    if (error === 'SYNC_FAILED') {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-amber-500">Data Sync Failed</h1>
                <p className="text-body mb-8">Experiment metadata loaded, but details could not be fetched.</p>
                <p className="text-zinc-500 text-sm mb-8 font-mono">Backend connection interrupted.</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }

    const { experiment, metrics, checkpoint, runResults, summaries, blocks } = data;

    const statObj: any = {};
    (summaries || []).forEach((row: any) => {
        statObj[row.alternative] = { ...row, alternative: row.alternative, count: row.total_runs };
    });
    const stats = statObj;

    let configYaml: any = null;
    try { if (experiment.config_content) configYaml = yaml.load(experiment.config_content); } catch (e) { }

    return (
        <div id="report-page-root" className="flex h-screen overflow-hidden">
            <RefreshOnInterval active={experiment.status === 'running' || experiment.status === 'RUNNING'} />
            {/* Context Sidebar (Left Pane) */}
            <ExperimentSidebar experiment={experiment} />

            {/* Main Content Area */}
            <section className="flex-1 h-full overflow-hidden flex flex-col bg-background">
                <ReportViewer
                    experiment={experiment}
                    initialContent={experiment.report_content || ""}
                    initialMetrics={metrics}
                    initialCheckpoint={checkpoint}
                    runResults={runResults}
                    stats={stats}
                    config={configYaml}
                    configContent={experiment.config_content || ""}
                    blocks={blocks || []}
                />
            </section>
        </div>
    );
}

export default function ClientReportPage({ id }: { id: string }) {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ReportPageContent id={id} />
        </Suspense>
    );
}
