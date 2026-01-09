import { RunResultRecord } from "@/app/api/api";
import { calculateStats, calculateSigTests } from "@/utils/statistics";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
interface PerformanceTableProps {
    runResults: RunResultRecord[];
    stats: any;
    controlBaseline?: string;
    alternatives?: string[];
}

export default function PerformanceTable({ runResults, stats, controlBaseline, alternatives: configAlts }: PerformanceTableProps) {
    const alternatives = configAlts || Object.keys(stats).sort();
    const referenceAlt = controlBaseline || (alternatives.length > 0 ? alternatives[0] : "");


    // Calculate significance relative to control
    const sigResults = calculateSigTests(runResults, referenceAlt);

    return (
        <div className="rounded-md border bg-card">
            <div className="p-4 border-b bg-muted/40 flex justify-between items-center">
                <h3 className="font-bold uppercase tracking-widest text-foreground">Performance Comparison</h3>
                <div className="flex gap-4 font-bold uppercase tracking-wider text-muted-foreground text-xs">
                    <span>Control: <span className="text-primary">{referenceAlt}</span></span>
                </div>
            </div>

            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="px-6">Alternative</TableHead>
                        <TableHead className="px-6 text-right">Success Rate</TableHead>
                        <TableHead className="px-6 text-right">Avg Duration</TableHead>
                        <TableHead className="px-6 text-right">Avg Tokens</TableHead>
                        <TableHead className="px-6 text-right">Avg Tool Calls</TableHead>
                        <TableHead className="px-6 text-right">Failed Tools</TableHead>
                        <TableHead className="px-6 text-right">Lint Issues</TableHead>
                        <TableHead className="px-6 text-right">Runs</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {alternatives.map((alt) => {
                        const s = stats[alt];
                        const sig = sigResults[alt] || {};
                        const successSig = sig.successRate || { level: '' };
                        const durationSig = sig.avgDuration || { level: '' };
                        const tokenSig = sig.avgTokens || { level: '' };
                        const toolCallSig = sig.avgToolCalls || { level: '' };

                        // Handle both snake_case (DB) and camelCase (client calc)
                        const successRate = s.success_rate !== undefined ? s.success_rate : s.successRate;
                        const avgDuration = s.avg_duration !== undefined ? s.avg_duration : s.avgDuration;
                        const avgTokens = s.avg_tokens !== undefined ? s.avg_tokens : s.avgTokens;
                        const avgLint = s.avg_lint !== undefined ? s.avg_lint : s.avgLint;
                        const totalRuns = s.total_runs !== undefined ? s.total_runs : s.count;
                        const successCount = s.success_count !== undefined ? s.success_count : s.successCount;

                        // Calculate avg tool calls if not present directly (DB summary has total, client has avg)
                        const avgToolCalls = s.avgToolCalls !== undefined
                            ? s.avgToolCalls
                            : (s.total_tool_calls && totalRuns ? s.total_tool_calls / totalRuns : 0);
                        
                        const avgFailedTools = (s.failed_tool_calls && totalRuns) ? s.failed_tool_calls / totalRuns : 0;

                        return (
                            <TableRow key={alt}>
                                <TableCell className="px-6 font-bold text-foreground">
                                    {alt}
                                    {alt === referenceAlt && <Badge variant="secondary" className="ml-2">Control</Badge>}
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-bold text-foreground">{(successRate || 0).toFixed(1)}%</span>
                                        {successSig.level && <span className="text-primary font-bold" title="Statistically Significant">{successSig.level}</span>}
                                    </div>
                                    <div className="text-muted-foreground text-xs mt-1">{successCount}/{totalRuns} runs</div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgDuration?.toFixed(2)}s</span>
                                        {durationSig.level && <span className="text-primary font-bold">{durationSig.level}</span>}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgTokens / 1000).toFixed(1)}k</span>
                                        {tokenSig.level && <span className="text-primary font-bold">{tokenSig.level}</span>}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgToolCalls?.toFixed(1)}</span>
                                        {toolCallSig.level && <span className="text-primary font-bold">{toolCallSig.level}</span>}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className={`font-mono ${avgFailedTools > 0 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                                        {avgFailedTools.toFixed(1)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right font-mono">
                                    {avgLint?.toFixed(1) || 0}
                                </TableCell>
                                <TableCell className="px-6 text-right font-mono text-muted-foreground">
                                    {totalRuns}
                                </TableCell>
                            </TableRow>
                        );
                    })}
                </TableBody>
            </Table>

            <div className="p-4 bg-muted/20 border-t flex gap-8 text-xs">
                <div className="flex items-center gap-2">
                    <span className="text-primary font-black">***</span>
                    <span className="text-muted-foreground uppercase font-bold tracking-tighter">p &lt; 0.01</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-primary font-black">**</span>
                    <span className="text-muted-foreground uppercase font-bold tracking-tighter">p &lt; 0.05</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-primary font-black">*</span>
                    <span className="text-muted-foreground uppercase font-bold tracking-tighter">p &lt; 0.1</span>
                </div>
            </div>
        </div>
    );
}
