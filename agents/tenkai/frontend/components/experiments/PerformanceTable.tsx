import { RunResultRecord } from "@/app/api/api";
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
                        const s = stats[alt]; // Backend summary stats

                        // Helper: Prefer backend P-values (Fisher/Welch) over client Z-test
                        const getSigLevel = (backendP: number | undefined) => {
                            if (backendP !== undefined) {
                                if (backendP >= 0) {
                                    if (backendP < 0.01) return '***';
                                    if (backendP < 0.05) return '**';
                                    if (backendP < 0.1) return '*';
                                }
                                return ''; // Valid backend result indicating no significance (or not calculated)
                            }
                            return '';
                        };

                        const isControl = alt === referenceAlt;
                        const successSigLevel = isControl ? '' : getSigLevel(s.p_success);
                        const durationSigLevel = isControl ? '' : getSigLevel(s.p_duration);
                        const tokenSigLevel = isControl ? '' : getSigLevel(s.p_tokens);
                        const toolCallSigLevel = isControl ? '' : getSigLevel(s.p_tool_calls);

                        // Handle both snake_case (DB) and camelCase (client calc)
                        const successRate = s.success_rate;
                        const avgDuration = s.avg_duration;
                        const avgTokens = s.avg_tokens;
                        const avgLint = s.avg_lint;
                        const totalRuns = s.total_runs;
                        const successCount = s.success_count;

                        // Calculate avg tool calls if not present directly (DB summary has total, client has avg)
                        const avgToolCalls = s.total_tool_calls && totalRuns ? s.total_tool_calls / totalRuns : 0;
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
                                        {successSigLevel && <span className="text-primary font-bold" title="Statistically Significant">{successSigLevel}</span>}
                                    </div>
                                    <div className="text-muted-foreground text-xs mt-1">{successCount}/{totalRuns} runs</div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgDuration?.toFixed(2)}s</span>
                                        {durationSigLevel && <span className="text-primary font-bold">{durationSigLevel}</span>}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgTokens / 1000).toFixed(1)}k</span>
                                        {tokenSigLevel && <span className="text-primary font-bold">{tokenSigLevel}</span>}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgToolCalls?.toFixed(1)}</span>
                                        {toolCallSigLevel && <span className="text-primary font-bold">{toolCallSigLevel}</span>}
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
