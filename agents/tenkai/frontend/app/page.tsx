import Link from "next/link";
import { getExperiments } from "@/app/api/api";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import { Plus, Terminal } from "lucide-react";

export default async function Home() {
    const experiments = await getExperiments();

    const sortedExperiments = [...experiments].sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

    const activeExperiments = sortedExperiments.filter(e => e.status === 'RUNNING' || e.status === 'running');
    const completedExperiments = sortedExperiments.filter(e => e.status !== 'RUNNING' && e.status !== 'running');

    return (
        <div className="p-6 space-y-8">
            <RefreshOnInterval active={activeExperiments.length > 0} />

            {/* Header / Status Bar */}
            <header className="flex justify-between items-center pb-6 border-b">
                <div>
                    <h1 className="text-3xl font-extrabold tracking-tight">Dashboard</h1>
                    <div className="flex gap-4 mt-1">
                        <span className="text-sm font-medium text-muted-foreground uppercase tracking-widest">
                            Active Processes: <span className={activeExperiments.length > 0 ? "text-primary" : "text-foreground"}>{activeExperiments.length}</span>
                        </span>
                    </div>
                </div>
                <div className="flex gap-3">
                    <Link href="/logs">
                        <Button variant="outline" size="sm">
                            <Terminal className="mr-2 h-4 w-4" /> Server Logs
                        </Button>
                    </Link>
                    <Link href="/experiments/new">
                        <Button size="sm">
                            <Plus className="mr-2 h-4 w-4" /> New Experiment
                        </Button>
                    </Link>
                </div>
            </header>

            {/* Active Runs Panel */}
            {activeExperiments.length > 0 && (
                <section className="space-y-4">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">Active Processes</h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {activeExperiments.map(exp => (
                            <Link href={`/experiments/${exp.id}`} key={exp.id}>
                                <Card className="hover:border-primary/50 transition-colors group">
                                    <CardHeader className="pb-2">
                                        <div className="flex justify-between items-start">
                                            <CardTitle className="text-base group-hover:text-primary transition-colors">{exp.name || `Exp #${exp.id}`}</CardTitle>
                                            <Badge variant="outline" className={cn(
                                                "uppercase",
                                                (exp.status?.toUpperCase() === 'RUNNING') && "border-blue-500/50 text-blue-500 animate-pulse"
                                            )}>{exp.status}</Badge>
                                        </div>
                                    </CardHeader>
                                    <CardContent>
                                        <div className="w-full bg-secondary h-1 rounded-full overflow-hidden mb-2">
                                            <div
                                                className="bg-primary h-full transition-all duration-500"
                                                style={{ width: `${exp.progress ? exp.progress.percentage : 0}%` }}
                                            />
                                        </div>
                                        <div className="flex justify-between text-xs font-mono text-muted-foreground">
                                            <span>{exp.progress?.completed} / {exp.progress?.total}</span>
                                            <span>{exp.progress ? Math.round(exp.progress.percentage) : 0}%</span>
                                        </div>
                                    </CardContent>
                                </Card>
                            </Link>
                        ))}
                    </div>
                </section>
            )}

            {/* Recent Activity Data Grid */}
            <section className="space-y-4">
                <div className="flex justify-between items-center">
                    <h3 className="text-sm font-bold uppercase tracking-widest text-muted-foreground">Recent Activity</h3>
                    <Link href="/experiments">
                        <Button variant="link" className="font-bold">View All</Button>
                    </Link>
                </div>

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
                            {completedExperiments.slice(0, 15).map(exp => (
                                <TableRow key={exp.id}>
                                    <TableCell className="font-mono text-muted-foreground">{exp.id}</TableCell>
                                    <TableCell>
                                        <Link href={`/experiments/${exp.id}`} className="hover:text-primary font-medium transition-colors">
                                            {exp.name || "—"}
                                        </Link>
                                    </TableCell>
                                    <TableCell>
                                        <Badge variant={
                                            exp.status?.toUpperCase() === 'COMPLETED' ? 'secondary' : 'outline'
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
                            {completedExperiments.length === 0 && (
                                <TableRow>
                                    <TableCell colSpan={6} className="h-24 text-center">No activity recorded.</TableCell>
                                </TableRow>
                            )}
                        </TableBody>
                    </Table>
                </div>
            </section>
        </div>
    );
}