import Link from "next/link";
import { getExperiments } from "@/app/api/api";
import ExperimentsHeader from "@/components/experiments/ExperimentsHeader";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";

export default async function ExperimentsPage() {
    const experiments = await getExperiments();

    // Sort by timestamp descending
    const sortedExperiments = [...experiments].sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    return (
        <div className="p-6 space-y-6">
            <ExperimentsHeader />

            <div className="rounded-md border bg-card">
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead className="w-[80px]">ID</TableHead>
                            <TableHead>Name</TableHead>
                            <TableHead className="w-[120px]">Status</TableHead>
                            <TableHead className="w-[100px] text-right">Success</TableHead>
                            <TableHead className="w-[100px] text-right">Duration</TableHead>
                            <TableHead className="w-[150px] text-right">Date</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {sortedExperiments.map((exp) => (
                            <TableRow key={exp.id}>
                                <TableCell className="font-mono text-muted-foreground">{exp.id}</TableCell>
                                <TableCell>
                                    <Link href={`/experiments/${exp.id}`} className="hover:text-primary font-medium transition-colors">
                                        {exp.name || "—"}
                                    </Link>
                                </TableCell>
                                <TableCell>
                                    <Badge variant={
                                        exp.status?.toUpperCase() === 'COMPLETED' ? 'secondary' :
                                            exp.status?.toUpperCase() === 'FAILED' ? 'destructive' : 'outline'
                                    } className={cn(
                                        "uppercase",
                                        exp.status?.toUpperCase() === 'COMPLETED' && "border-green-500/50 text-green-500",
                                        exp.status?.toUpperCase() === 'RUNNING' && "border-blue-500/50 text-blue-500 animate-pulse",
                                        exp.status?.toUpperCase() === 'ABORTED' && "border-amber-500/50 text-amber-500"
                                    )}>
                                        {exp.status}
                                    </Badge>
                                </TableCell>
                                <TableCell className="text-right font-mono">
                                    <span className={cn(
                                        (exp.success_rate || 0) >= 90 ? "text-green-500" :
                                            (exp.success_rate || 0) >= 50 ? "text-yellow-500" : "text-destructive"
                                    )}>
                                        {(exp.success_rate || 0).toFixed(0)}%
                                    </span>
                                </TableCell>
                                <TableCell className="text-right font-mono text-muted-foreground">
                                    {(exp.avg_duration || 0).toFixed(1)}s
                                </TableCell>
                                <TableCell className="text-right font-mono text-muted-foreground">
                                    {new Date(exp.timestamp).toLocaleDateString()}
                                </TableCell>
                            </TableRow>
                        ))}
                        {sortedExperiments.length === 0 && (
                            <TableRow>
                                <TableCell colSpan={6} className="h-24 text-center">
                                    No experiments found. <Link href="/experiments/new" className="text-primary hover:underline font-bold">Create one</Link>.
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
}

