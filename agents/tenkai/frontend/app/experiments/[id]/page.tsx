import yaml from "js-yaml";
import { getSimplifiedMetrics, getCheckpoint, getRunResults, getExperimentSummaries, getExperiment } from "@/app/api/api";
import ReportViewer from "@/components/ReportViewer";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import Link from "next/link";
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
                <Link href="/experiments" className="text-body hover:underline font-bold text-[#6366f1]">Return to index</Link>
            </div>
        );
    }

    if (!experiment) {

        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-red-500">404</h1>
                <p className="text-body mb-8">Study Purged</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-[#6366f1]">Return to index</Link>
            </div>
        );
    }
    let metrics, checkpoint, runResults, summaries;
    try {
        [metrics, checkpoint, runResults, summaries] = await Promise.all([
            getSimplifiedMetrics(experiment.id),
            getCheckpoint(String(experiment.id)),
            getRunResults(String(experiment.id)),
            getExperimentSummaries(experiment.id)
        ]);
    } catch (e) {
        return (
            <div className="p-8 text-center py-32">
                <h1 className="text-title mb-4 text-amber-500">Data Sync Failed</h1>
                <p className="text-body mb-8">Experiment metadata loaded, but details could not be fetched.</p>
                <p className="text-zinc-500 text-sm mb-8 font-mono">Backend connection interrupted.</p>
                <Link href="/experiments" className="text-body hover:underline font-bold text-[#6366f1]">Return to index</Link>
            </div>
        );
    }


    const statObj: any = {};
    summaries.forEach(row => {
        statObj[row.alternative] = { ...row, alternative: row.alternative, count: row.total_runs };
    });
    const stats = statObj;

    let configYaml: any = null;
    try { if (experiment.config_content) configYaml = yaml.load(experiment.config_content); } catch (e) { }

    return (
        <div className="flex h-screen overflow-hidden">
            <RefreshOnInterval active={experiment.status === 'running' || experiment.status === 'RUNNING'} />
            {/* Context Sidebar (Left Pane) */}
            <aside className="w-[300px] border-r border-[#27272a] bg-[#09090b] flex flex-col h-full">
                <div className="p-4 border-b border-[#27272a]">
                    <Link href="/experiments" className="text-body hover:text-white flex items-center mb-4 transition-colors font-bold uppercase tracking-wider">
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 19l-7-7m0 0l7-7m-7 7h18"></path></svg>
                        Back
                    </Link>
                    <h1 className="text-title leading-tight mb-2">{experiment.name || "Unnamed"}</h1>
                    <div className="flex items-center gap-2">
                        <span className={`inline-block w-2.5 h-2.5 rounded-full ${experiment.status?.toUpperCase() === 'RUNNING' ? 'bg-[#6366f1] animate-pulse shadow-[0_0_8px_#6366f1]' : (experiment.status?.toUpperCase() === 'COMPLETED' ? 'bg-emerald-500' : 'bg-[#3f3f46]')}`}></span>
                        <span className="text-body font-bold uppercase">{experiment.status}</span>
                    </div>
                </div>

                <div className="p-4 space-y-8 overflow-y-auto flex-1 text-body">
                    <div>
                        <h3 className="font-bold uppercase tracking-widest mb-2 opacity-50">Description</h3>
                        <p className="leading-relaxed">
                            {experiment.description || "No description provided."}
                        </p>
                    </div>

                    <div className="space-y-4">
                        <h3 className="font-bold uppercase tracking-widest opacity-50">Metadata</h3>
                        <div className="grid grid-cols-2 gap-y-3">
                            <span className="uppercase opacity-50">ID</span>
                            <span className="text-[#f4f4f5] text-right font-mono font-bold">{experiment.id}</span>

                            <span className="uppercase opacity-50">Started</span>
                            <span className="text-[#f4f4f5] text-right">{new Date(experiment.timestamp).toLocaleDateString()}</span>

                            <span className="uppercase opacity-50">Control</span>
                            <span className="text-[#6366f1] text-right font-bold">{experiment.experiment_control || "—"}</span>
                        </div>
                    </div>
                </div>
            </aside>

            {/* Main Content Area */}
            <main className="flex-1 h-full overflow-hidden flex flex-col bg-[#09090b]">
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
