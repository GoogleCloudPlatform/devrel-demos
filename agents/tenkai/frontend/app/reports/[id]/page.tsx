import Link from "next/link";
import yaml from "js-yaml";
import { getExperimentById, getSimplifiedMetrics, getCheckpoint, getRunResults } from "@/lib/api";
import ReportViewer from "@/components/ReportViewer";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import { calculateStats } from "@/lib/statistics";
import DeleteExperimentButton from "@/components/DeleteExperimentButton";
import RelaunchButton from "@/components/RelaunchButton";

export default async function ReportPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = await params;
    const experiment = await getExperimentById(id);

    if (!experiment) {
        return (
            <div className="p-10">
                <h1 className="text-2xl font-bold">Report not found</h1>
                <Link href="/" className="text-blue-400 mt-4 block">← Back to Dashboard</Link>
            </div>
        );
    }

    // Use DB content directly
    const content = experiment.report_content || "";
    // Config parsing from DB content
    let config: any = null;
    try {
        if (experiment.config_content) {
            console.log(`[ReportPage] Config content found (${experiment.config_content.length} chars)`);
            config = yaml.load(experiment.config_content);
        } else {
            console.warn(`[ReportPage] No config_content for experiment ${id}`);
        }
    } catch (e) {
        console.error("Failed to parse config from DB", e);
    }

    const metrics = await getSimplifiedMetrics(experiment.id);
    const checkpoint = await getCheckpoint(String(experiment.id));
    const runResults = await getRunResults(String(experiment.id));
    const summaries = await import("@/lib/api").then(api => api.getExperimentSummaries(id));

    const stats: any = {};
    summaries.forEach(s => {
        stats[s.alternative] = {
            alternative: s.alternative,
            count: s.total_runs,
            successCount: s.success_count,
            successRate: s.success_rate,
            avgDuration: s.avg_duration,
            avgTokens: s.avg_tokens,
            avgLint: s.avg_lint,
            totalLint: Math.round(s.avg_lint * s.total_runs),
            durations: [], // No longer needed for calc if we have p-values
            successes: [],
            // Inject pre-calculated p-values from Go
            pDuration: s.p_duration,
            pSuccess: s.p_success,
            pTokens: s.p_tokens,
            pLint: s.p_lint,
            pTestsPassed: s.p_tests_passed,
            pTestsFailed: s.p_tests_failed,
            avgTestsPassed: s.avg_tests_passed,
            avgTestsFailed: s.avg_tests_failed
        };
    });

    // If no summaries yet (e.g. experiment still running), fallback to client-side calc
    const effectiveStats = summaries.length > 0 ? stats : calculateStats(runResults);

    const isActive = experiment.status === 'running' || experiment.status === 'paused';
    const altNames = Object.keys(effectiveStats);
    // Determine reference (prefer explicit control, then first in config, then first in stats)
    const referenceAlt = experiment.experiment_control || config?.alternatives?.[0]?.name || altNames[0];

    return (
        <div className="p-10 space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto">
            <RefreshOnInterval active={isActive} />

            {/* Header */}
            <header className="flex justify-between items-start border-b border-white/5 pb-8">
                <div>
                    <Link href="/" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Dashboard</Link>
                    <h1 className="text-4xl font-bold tracking-tight mt-2">{experiment.name || "Experiment Report"}</h1>
                    <div className="flex items-center gap-4 mt-2">
                        <span className="text-zinc-500 text-sm font-mono">{new Date(experiment.timestamp).toLocaleString()}</span>
                        <span className="text-zinc-600 text-sm">•</span>
                        <span className="text-zinc-500 text-sm font-mono">ID: {experiment.id}</span>
                        {experiment.experiment_control && (
                            <span className="text-[10px] bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/20 font-bold uppercase tracking-wider">
                                Control: {experiment.experiment_control}
                            </span>
                        )}
                    </div>
                    {experiment.description && (
                        <p className="text-zinc-400 mt-4 max-w-3xl leading-relaxed text-lg">{experiment.description}</p>
                    )}
                </div>
                <div className="flex gap-4 items-center">
                    <RelaunchButton id={experiment.id} />
                    <span className={`px-4 py-1.5 rounded-full text-sm font-bold uppercase tracking-widest border ${experiment.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20' :
                        experiment.status === 'running' ? 'bg-blue-500/10 text-blue-500 border-blue-500/20 animate-pulse' :
                            'bg-amber-500/10 text-amber-500 border-amber-500/20'
                        }`}>
                        {experiment.status}
                    </span>
                    <DeleteExperimentButton id={experiment.id} name={experiment.name} />
                </div>
            </header>

            <ReportViewer
                experiment={experiment}
                initialContent={content}
                initialMetrics={metrics}
                initialCheckpoint={checkpoint}
                runResults={runResults}
                stats={effectiveStats}
                config={config}
                configContent={experiment.config_content}
            />

            <footer className="pt-10 border-t border-white/5 text-zinc-600 text-[10px] flex justify-between items-center uppercase font-bold tracking-widest">
                <div className="flex gap-4">
                    <span>Experiment ID: {experiment.id}</span>
                </div>
            </footer>
        </div>
    );
}
