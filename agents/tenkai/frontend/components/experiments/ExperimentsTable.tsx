'use client';

import { useState, useEffect } from "react";
import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import ProgressBar from "@/components/ui/progress-bar";
import { ExperimentRecord } from "@/types/domain";
import { toggleLock } from "@/lib/api";
import LockToggle from "@/components/LockToggle";
import { useRouter } from "next/navigation";

interface ExperimentsTableProps {
    experiments: ExperimentRecord[];
}

function ClientOnlyDate({ date }: { date: string | number | Date }) {
    const [mounted, setMounted] = useState(false);
    useEffect(() => {
        setMounted(true);
    }, []);

    if (!mounted) return <span className="opacity-0">Loading...</span>;
    return <>{new Date(date).toLocaleString()}</>;
}

export default function ExperimentsTable({ experiments }: ExperimentsTableProps) {
    const router = useRouter();

    const handleToggleLock = async (id: number, locked: boolean) => {
        const success = await toggleLock(id, locked);
        if (success) {
            router.refresh(); // Refresh to update UI state
        }
        return success;
    };

    return (
        <div className="rounded-md border bg-card text-body">
            <Table>
                <TableHeader>
                    <TableRow>
                        <TableHead className="w-[80px]">ID</TableHead>
                        <TableHead className="w-[120px]">Status</TableHead>
                        <TableHead className="w-[350px]">Name</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead className="w-[150px]">Control</TableHead>
                        <TableHead className="w-[110px] text-right">Alternatives</TableHead>
                        <TableHead className="w-[200px] text-right">Sample Size (Repetitions)</TableHead>
                        <TableHead className="w-[110px] text-right">Concurrency</TableHead>
                        <TableHead className="w-[100px] text-right">Jobs</TableHead>
                        <TableHead className="w-[100px] text-right">Timeout</TableHead>
                        <TableHead className="w-[150px]">Progress</TableHead>
                        <TableHead className="w-[150px] text-right">Date</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {experiments.map((exp) => (
                        <TableRow key={exp.id} className={exp.is_locked ? "border-l-2 border-l-warning" : ""}>
                            <TableCell className="font-mono text-muted-foreground font-bold flex items-center gap-2">
                                <span>#{exp.id}</span>
                                <LockToggle
                                    locked={!!exp.is_locked}
                                    onToggle={(locked) => handleToggleLock(exp.id, locked)}
                                />
                            </TableCell>
                            <TableCell>
                                <Badge variant={
                                    exp.status?.toUpperCase() === 'COMPLETED' ? 'secondary' :
                                        exp.status?.toUpperCase() === 'FAILED' ? 'destructive' : 'outline'
                                } className={cn(
                                    "uppercase font-bold tracking-wider text-[10px]",
                                    exp.status?.toUpperCase() === 'COMPLETED' && "border-success/50 text-success bg-success/10",
                                    exp.status?.toUpperCase() === 'RUNNING' && "border-primary/50 text-primary bg-primary/10 animate-pulse",
                                    exp.status?.toUpperCase() === 'ABORTED' && "border-muted-foreground/50 text-muted-foreground bg-muted",
                                    exp.status?.toUpperCase() === 'QUEUED' && "border-info/50 text-info bg-info/10"
                                )}>
                                    {exp.status}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                <Link href={`/experiments/view?id=${exp.id}`} className="hover:text-primary font-bold text-base transition-colors truncate block max-w-[350px]" title={exp.name}>
                                    {exp.name || "Unnamed Experiment"}
                                </Link>
                            </TableCell>
                            <TableCell>
                                <p className="text-sm text-muted-foreground truncate max-w-[500px]" title={exp.description}>
                                    {exp.description || "—"}
                                </p>
                            </TableCell>
                            <TableCell className="text-muted-foreground font-mono text-xs truncate max-w-[150px]" title={exp.experiment_control}>
                                {exp.experiment_control || "—"}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                                {exp.num_alternatives || "?"}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                                {exp.reps || 1}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                                {exp.concurrent || 1}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                                {exp.total_jobs || "-"}
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground">
                                {exp.timeout || "-"}
                            </TableCell>

                            <TableCell>
                                <ProgressBar
                                    percentage={exp.progress?.percentage || 0}
                                    completed={exp.progress?.completed || 0}
                                    total={exp.progress?.total || 0}
                                    status={exp.status}
                                />
                            </TableCell>
                            <TableCell className="text-right font-mono text-muted-foreground text-xs whitespace-nowrap">
                                <ClientOnlyDate date={exp.timestamp} />
                            </TableCell>
                        </TableRow>
                    ))}
                    {experiments.length === 0 && (
                        <TableRow>
                            <TableCell colSpan={12} className="h-24 text-center text-muted-foreground">
                                No experiments found. <Link href="/experiments/new" className="text-primary hover:underline font-bold">Launch your first experiment</Link>.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    );
}
