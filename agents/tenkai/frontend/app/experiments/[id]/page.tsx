import yaml from "js-yaml";
import { getSimplifiedMetrics, getCheckpoint, getRunResults, getExperimentSummaries, getExperiment } from "@/app/api/api";
import ReportViewer from "@/components/ReportViewer";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import ExperimentLockToggle from "@/components/experiments/ExperimentLockToggle";
import Link from "next/link";
import ExperimentSidebar from "@/components/experiments/ExperimentSidebar";
import { Suspense } from "react";

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
    // 1. Fetch Experiment Data
    let experiment;
    try {
        experiment = await getExperiment(parseInt((await params).id));
    } catch (e) {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-red-500">Connection Failed</h1>
                <p className="text-body mb-8">Could not connect to the Tenkai backend.</p>
                <p className="text-zinc-500 text-sm mb-8 font-mono">Ensure 'tenkai --serve' is running.</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }

    if (!experiment) {

        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-red-500">404</h1>
                <p className="text-body mb-8">Study Purged</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }
    let metrics, checkpoint, runResults, summaries;
    try {
        [metrics, checkpoint, runResults, summaries] = await Promise.all([
            getSimplifiedMetrics(experiment.id),
            getCheckpoint(String(experiment.id)),
            getRunResults(String(experiment.id), 1, 5000),
            getExperimentSummaries(experiment.id)
        ]);
    } catch (e) {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-amber-500">Data Sync Failed</h1>
                <p className="text-body mb-8">Experiment metadata loaded, but details could not be fetched.</p>
                <p className="text-zinc-500 text-sm mb-8 font-mono">Backend connection interrupted.</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-primary">Return to index</Link>
            </div>
        );
    }


    const statObj: any = {};
    (summaries || []).forEach(row => {
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
            <main className="flex-1 h-full overflow-hidden flex flex-col bg-background">
                <Suspense fallback={<div className="p-10 text-center opacity-50">Loading Report...</div>}>
                    <ReportViewer
                        experiment={experiment}
                        initialContent={experiment.report_content || ""}
                        initialMetrics={metrics}
                        initialCheckpoint={checkpoint}
                        runResults={runResults}
                        stats={stats}
                        config={configYaml}
                        configContent={experiment.config_content || ""}
                    />
                </Suspense>
            </main>
        </div>
    );
}
