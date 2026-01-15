import Link from "next/link";
import { getExperiments } from "@/app/api/api";
import RefreshOnInterval from "@/components/RefreshOnInterval";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/utils/cn";
import { Plus, Terminal } from "lucide-react";
import ProgressBar from "@/components/ui/progress-bar";
import ExperimentsTable from "@/components/experiments/ExperimentsTable";

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
                                        <ProgressBar
                                            percentage={exp.progress?.percentage || 0}
                                            completed={exp.progress?.completed || 0}
                                            total={exp.progress?.total || 0}
                                            status={exp.status}
                                        />
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

                <ExperimentsTable experiments={completedExperiments.slice(0, 15)} />
            </section>
        </div>
    );
}