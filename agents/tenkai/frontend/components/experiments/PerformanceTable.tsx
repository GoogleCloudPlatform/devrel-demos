import { RunResultRecord } from "@/app/api/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import { ArrowUpDown } from "lucide-react";
import { useState } from "react";
interface PerformanceTableProps {
    runResults: RunResultRecord[];
    stats: any;
    controlBaseline?: string;
    alternatives?: string[];
    onAlternativeClick?: (alt: string) => void;
}

export default function PerformanceTable({ runResults, stats, controlBaseline, alternatives: configAlts, onAlternativeClick }: PerformanceTableProps) {
    const [sortConfig, setSortConfig] = useState<{ key: string; direction: 'asc' | 'desc' } | null>(null);

    const handleSort = (key: string) => {
        setSortConfig(current => {
            if (current?.key === key) {
                return { key, direction: current.direction === 'asc' ? 'desc' : 'asc' };
            }
            return { key, direction: 'desc' };
        });
    };

    const sortedAlternatives = [...(configAlts || Object.keys(stats))].sort((a, b) => {
        if (!sortConfig) return 0;

        if (sortConfig.key === 'alternative') {
            return sortConfig.direction === 'asc'
                ? a.localeCompare(b)
                : b.localeCompare(a);
        }

        const statsA = stats[a];
        const statsB = stats[b];

        // Handle derived metrics if needed, otherwise direct access
        let valA = statsA[sortConfig.key];
        let valB = statsB[sortConfig.key];

        // Specific derived metrics handling
        if (sortConfig.key === 'avg_input_tokens') valA = statsA.avg_input_tokens || 0;
        if (sortConfig.key === 'avg_input_tokens') valB = statsB.avg_input_tokens || 0;
        if (sortConfig.key === 'avg_output_tokens') valA = statsA.avg_output_tokens || 0;
        if (sortConfig.key === 'avg_output_tokens') valB = statsB.avg_output_tokens || 0;
        if (sortConfig.key === 'avg_cached_tokens') valA = statsA.avg_cached_tokens || 0;
        if (sortConfig.key === 'avg_cached_tokens') valB = statsB.avg_cached_tokens || 0;

        // Tool calls (derived averages)
        if (sortConfig.key === 'avg_tool_calls') {
            valA = (statsA.total_tool_calls && statsA.total_runs) ? statsA.total_tool_calls / statsA.total_runs : 0;
            valB = (statsB.total_tool_calls && statsB.total_runs) ? statsB.total_tool_calls / statsB.total_runs : 0;
        }
        if (sortConfig.key === 'avg_failed_tools') {
            valA = (statsA.failed_tool_calls && statsA.total_runs) ? statsA.failed_tool_calls / statsA.total_runs : 0;
            valB = (statsB.failed_tool_calls && statsB.total_runs) ? statsB.failed_tool_calls / statsB.total_runs : 0;
        }

        if (sortConfig.key === 'avg_coverage') {
            valA = statsA.avg_coverage || 0;
            valB = statsB.avg_coverage || 0;
        }

        if (valA < valB) return sortConfig.direction === 'asc' ? -1 : 1;
        if (valA > valB) return sortConfig.direction === 'asc' ? 1 : -1;
        return 0;
    });

    const alternatives = sortedAlternatives;
    const referenceAlt = controlBaseline || (alternatives.length > 0 ? alternatives[0] : "");


    return (
        <div className="rounded-md border bg-card">
            <div className="p-4 border-b bg-muted/40 flex justify-between items-center">
                <h3 className="font-bold uppercase tracking-widest text-foreground">Experiment Summary</h3>
                <div className="flex gap-4 font-bold uppercase tracking-wider text-muted-foreground text-xs">
                    <span>Control: <span className="text-primary">{referenceAlt}</span></span>
                </div>
            </div>

            <Table>
                <TableHeader>
                    <TableRow className="bg-muted/50">
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors border-r border-border text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('alternative')}>
                            <div className="flex items-center justify-center gap-2">Alternative <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors border-r border-border text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('success_rate')}>
                            <div className="flex items-center justify-center gap-2">Success Rate <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors border-r border-border text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('avg_duration')}>
                            <div className="flex items-center justify-center gap-2">Avg Duration <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                        <TableHead colSpan={4} className="px-6 text-center border-b border-border border-r border-border py-2 h-auto text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            Token Usage
                        </TableHead>
                        <TableHead colSpan={2} className="px-6 text-center border-b border-border border-r border-border py-2 h-auto text-xs font-bold uppercase tracking-wider text-muted-foreground">
                            Tool Usage
                        </TableHead>
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors border-r border-border text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('avg_lint')}>
                            <div className="flex items-center justify-center gap-2">Avg Lint <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors border-r border-border text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('avg_coverage')}>
                            <div className="flex items-center justify-center gap-2">Avg Cov <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                        <TableHead rowSpan={2} className="px-6 h-auto align-bottom pb-3 cursor-pointer hover:bg-accent transition-colors text-xs font-bold uppercase tracking-wider text-muted-foreground text-center" onClick={() => handleSort('total_runs')}>
                            <div className="flex items-center justify-center gap-2">Runs <ArrowUpDown size={12} className="opacity-50" /></div>
                        </TableHead>
                    </TableRow>
                    <TableRow className="bg-muted/50 border-t-0">
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_tokens')}>
                            Total <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_input_tokens')}>
                            Input <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_output_tokens')}>
                            Output <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_cached_tokens')}>
                            Cached <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_tool_calls')}>
                            Total <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                        <TableHead className="px-6 py-2 border-r border-border text-right cursor-pointer hover:bg-accent hover:text-accent-foreground text-xs font-bold text-muted-foreground" onClick={() => handleSort('avg_failed_tools')}>
                            Failed <ArrowUpDown size={10} className="inline ml-1 opacity-50" />
                        </TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {alternatives.map((alt) => {
                        const s = stats[alt]; // Backend summary stats
                        if (!s) return null; // Handle missing data


                        // Helper: Prefer backend P-values (Fisher/Welch) over client Z-test
                        const getSigLevel = (backendP: number | undefined, effectD: number | undefined) => {
                            if (backendP !== undefined) {
                                if (backendP >= 0) {
                                    let stars = '';
                                    if (backendP < 0.001) stars = '***';
                                    else if (backendP < 0.01) stars = '**';
                                    else if (backendP < 0.05) stars = '*';

                                    if (!stars) return null;

                                    // Classify effect size
                                    let effectDesc = '';
                                    if (effectD !== undefined && effectD !== 0) {
                                        const absD = Math.abs(effectD);
                                        if (absD < 0.2) effectDesc = 'Negligible';
                                        else if (absD < 0.5) effectDesc = 'Small';
                                        else if (absD < 0.8) effectDesc = 'Medium';
                                        else effectDesc = 'Large';
                                        effectDesc = ` (d=${effectD.toFixed(2)}, ${effectDesc})`;
                                    }

                                    return {
                                        label: stars,
                                        title: `p=${backendP.toFixed(4)}${effectDesc}`
                                    };
                                }
                            }
                            return null;
                        };

                        const isControl = alt === referenceAlt;
                        const successSig = isControl ? null : getSigLevel(s.p_success, undefined); // Fisher doesn't have d
                        const durationSig = isControl ? null : getSigLevel(s.p_duration, s.effect_duration);
                        const tokenSig = isControl ? null : getSigLevel(s.p_tokens, s.effect_tokens);
                        const inputTokenSig = isControl ? null : getSigLevel(s.p_input_tokens, s.effect_input_tokens);
                        const outputTokenSig = isControl ? null : getSigLevel(s.p_output_tokens, s.effect_output_tokens);
                        const cachedTokenSig = isControl ? null : getSigLevel(s.p_cached_tokens, s.effect_cached_tokens);
                        const toolCallSig = isControl ? null : getSigLevel(s.p_tool_calls, undefined);
                        const failedToolSig = isControl ? null : getSigLevel(s.p_failed_tool_calls, undefined);
                        const coverageSig = (!isControl && s.p_coverage !== undefined) ? getSigLevel(s.p_coverage, s.effect_coverage) : null;

                        // Handle both snake_case (DB) and camelCase (client calc)
                        const successRate = s.success_rate;
                        const avgDuration = s.avg_duration;
                        const avgTokens = s.avg_tokens;
                        const avgInputTokens = s.avg_input_tokens || 0;
                        const avgOutputTokens = s.avg_output_tokens || 0;
                        const avgCachedTokens = s.avg_cached_tokens || 0;
                        const avgLint = s.avg_lint;
                        const totalRuns = s.total_runs;
                        const successCount = s.success_count;

                        // Calculate avg tool calls if not present directly (DB summary has total, client has avg)
                        const avgToolCalls = s.total_tool_calls && totalRuns ? s.total_tool_calls / totalRuns : 0;
                        const avgFailedTools = (s.failed_tool_calls && totalRuns) ? s.failed_tool_calls / totalRuns : 0;

                        const renderSig = (sig: { label: string, title: string } | null) => {
                            if (!sig) return null;
                            return (
                                <Tooltip>
                                    <TooltipTrigger asChild>
                                        <span className="text-primary font-bold cursor-help ml-1">{sig.label}</span>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                        <p>{sig.title}</p>
                                    </TooltipContent>
                                </Tooltip>
                            );
                        };

                        return (
                            <TableRow key={alt}>
                                <TableCell
                                    className={`px-6 font-bold text-foreground border-r border-border ${onAlternativeClick ? 'cursor-pointer hover:text-accent-foreground transition-colors hover:bg-accent' : ''}`}
                                    onClick={() => onAlternativeClick?.(alt)}
                                >
                                    {alt}
                                    {alt === referenceAlt && <Badge variant="secondary" className="ml-2">Control</Badge>}
                                </TableCell>
                                <TableCell className="px-6 text-right border-r border-border">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-bold text-foreground">{(successRate || 0).toFixed(1)}%</span>
                                        {renderSig(successSig)}
                                    </div>
                                    <div className="text-muted-foreground text-xs mt-1">{successCount}/{totalRuns} runs</div>
                                </TableCell>
                                <TableCell className="px-6 text-right border-r border-border">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgDuration?.toFixed(2)}s</span>
                                        {renderSig(durationSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right border-l border-border">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgTokens / 1000).toFixed(1)}k</span>
                                        {renderSig(tokenSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgInputTokens / 1000).toFixed(1)}k</span>
                                        {renderSig(inputTokenSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgOutputTokens / 1000).toFixed(1)}k</span>
                                        {renderSig(outputTokenSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right border-r border-white/5">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(avgCachedTokens / 1000).toFixed(1)}k</span>
                                        {renderSig(cachedTokenSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{avgToolCalls?.toFixed(1)}</span>
                                        {renderSig(toolCallSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right border-r border-white/5">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className={`font-mono ${avgFailedTools > 0 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                                            {avgFailedTools.toFixed(1)}
                                        </span>
                                        {renderSig(failedToolSig)}
                                    </div>
                                </TableCell>
                                <TableCell className="px-6 text-right font-mono border-r border-white/5">
                                    {avgLint?.toFixed(1) || 0}
                                </TableCell>
                                <TableCell className="px-6 text-right border-r border-white/5">
                                    <div className="flex items-center justify-end gap-2">
                                        <span className="font-mono">{(s.avg_coverage || 0).toFixed(1)}%</span>
                                        {renderSig(coverageSig)}
                                    </div>
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
