"use client";

import { ExperimentSummaryRecord } from "@/app/api/api";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";

interface ToolImpactTableProps {
    stats: Record<string, ExperimentSummaryRecord>;
    alternatives: string[];
}

export default function ToolImpactTable({ stats, alternatives }: ToolImpactTableProps) {
    const impacts: any[] = [];

    // Filter out "Combined" from the regular list to handle it specially
    const regularAlts = alternatives.filter(a => a !== "Combined");
    const hasCombined = alternatives.includes("Combined");

    const processAlt = (alt: string, isGlobal: boolean) => {
        const row = stats[alt];
        if (!row || !row.tool_analysis) return;

        row.tool_analysis.forEach((ta: any) => {
            // Only include tools with significant P-values (P < 0.1)
            if (ta.succ_fail_p_value >= 0 && ta.succ_fail_p_value < 0.1) {
                impacts.push({
                    alt: alt,
                    tool: ta.tool_name,
                    p: ta.succ_fail_p_value,
                    corr_dur: ta.duration_corr,
                    isGlobal
                });
            }
        });
    };

    if (hasCombined) processAlt("Combined", true);
    regularAlts.forEach(alt => processAlt(alt, false));

    // Sort: Global first, then by p-value
    impacts.sort((a, b) => {
        if (a.isGlobal !== b.isGlobal) return a.isGlobal ? -1 : 1;
        return a.p - b.p;
    });

    if (impacts.length === 0) return null;

    return (
        <div className="panel overflow-hidden mt-6 border-primary/20 shadow-sm">
            <div className="p-4 border-b border-primary/20 bg-primary/10 flex justify-between items-center">
                <div className="flex items-center gap-2">
                    <h3 className="font-bold uppercase tracking-widest text-sm text-primary">Success Determinants Analysis</h3>
                    <Badge variant="outline" className="text-[10px] bg-primary/10 border-primary/30 text-primary">Statistical Impact</Badge>
                </div>
                <span className="text-xs text-muted-foreground font-mono font-bold tracking-tighter">Mann-Whitney U Test (Succ vs Fail)</span>
            </div>
            <div className="overflow-x-auto">
                <Table>
                    <TableHeader>
                        <TableRow className="hover:bg-transparent text-muted-foreground uppercase text-[10px] font-bold tracking-widest border-white/5">
                            <TableHead className="w-[180px] px-6">Scope / Context</TableHead>
                            <TableHead className="w-[180px] px-6">Tool Identifier</TableHead>
                            <TableHead className="text-right px-6">Significance (P-Value)</TableHead>
                            <TableHead className="text-right px-6">Speed Impact (Rho)</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {impacts.map((imp, i) => {
                            let sig = "";
                            if (imp.p < 0.01) sig = "***";
                            else if (imp.p < 0.05) sig = "**";
                            else if (imp.p < 0.1) sig = "*";

                            const isSignificant = imp.p < 0.1;
                            const rowBg = imp.isGlobal ? "bg-primary/[0.03]" : "";

                            return (
                                <TableRow key={i} className={`hover:bg-primary/10 transition-colors border-white/5 ${rowBg}`}>
                                    <TableCell className="px-6 font-mono text-[11px]">
                                        {imp.isGlobal ? (
                                            <span className="text-primary font-bold tracking-tighter uppercase">✨ Global (Combined)</span>
                                        ) : (
                                            <span className="text-muted-foreground">{imp.alt}</span>
                                        )}
                                    </TableCell>
                                    <TableCell className={`px-6 font-mono font-bold ${isSignificant ? 'text-primary' : 'text-muted-foreground'}`}>
                                        {imp.tool}
                                    </TableCell>
                                    <TableCell className="px-6 text-right font-mono">
                                        <div className="flex items-center justify-end gap-2">
                                            <span className={isSignificant ? "text-foreground font-bold" : "text-muted-foreground"}>
                                                {imp.p.toFixed(4)}
                                            </span>
                                            <span className="w-8 text-left text-primary font-black">{sig}</span>
                                        </div>
                                    </TableCell>
                                    <TableCell className={`px-6 text-right font-mono ${Math.abs(imp.corr_dur) > 0.5 ? 'text-yellow-500' : 'text-muted-foreground'}`}>
                                        <div className="flex items-center justify-end gap-1">
                                            {imp.corr_dur > 0.2 ? "🐢 " : (imp.corr_dur < -0.2 ? "⚡ " : "")}
                                            {imp.corr_dur.toFixed(2)}
                                        </div>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </div>
            <div className="p-3 bg-primary/5 text-[10px] text-muted-foreground italic flex gap-6 px-6">
                <span>**P-Value**: Probability that tool usage frequency is independent of run success.</span>
                <span>**Rho**: Spearman correlation with duration (positive = slower).</span>
            </div>
        </div>
    );
}
