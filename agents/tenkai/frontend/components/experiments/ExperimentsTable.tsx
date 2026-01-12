import Link from "next/link";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import ProgressBar from "@/components/ui/progress-bar";
import { ExperimentRecord } from "@/types/domain";

interface ExperimentsTableProps {
    experiments: ExperimentRecord[];
}

export default function ExperimentsTable({ experiments }: ExperimentsTableProps) {
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
                        <TableRow key={exp.id}>
                            <TableCell className="font-mono text-muted-foreground font-bold">#{exp.id}</TableCell>
                            <TableCell>
                                <Badge variant={
                                    exp.status?.toUpperCase() === 'COMPLETED' ? 'secondary' :
                                        exp.status?.toUpperCase() === 'FAILED' ? 'destructive' : 'outline'
                                } className={cn(
                                    "uppercase font-bold tracking-wider text-[10px]",
                                    exp.status?.toUpperCase() === 'COMPLETED' && "border-emerald-500/50 text-emerald-500 bg-emerald-500/10",
                                    exp.status?.toUpperCase() === 'RUNNING' && "border-indigo-500/50 text-indigo-400 bg-indigo-500/10 animate-pulse",
                                    exp.status?.toUpperCase() === 'ABORTED' && "border-zinc-500/50 text-zinc-400 bg-zinc-500/10",
                                    exp.status?.toUpperCase() === 'QUEUED' && "border-blue-500/50 text-blue-400 bg-blue-500/10"
                                )}>
                                    {exp.status}
                                </Badge>
                            </TableCell>
                            <TableCell>
                                <Link href={`/experiments/${exp.id}`} className="hover:text-primary font-bold text-base transition-colors truncate block max-w-[350px]" title={exp.name}>
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
                                {new Date(exp.timestamp).toLocaleString()}
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
