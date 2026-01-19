import { Card } from "@/components/ui/card";

export default function MetricsOverview({ metrics }: { metrics: any }) {
    if (!metrics) return null;

    const cards = [
        { label: 'Total Executions', value: metrics.total, subtext: 'Baseline reps', color: 'text-foreground' },
        { label: 'Successful Runs', value: metrics.successful, subtext: 'Verified results', color: 'text-emerald-500' },
        { label: 'Avg Success Rate', value: metrics.successRate, subtext: 'Benchmark mean', color: 'text-primary' },
        { label: 'Avg Duration', value: metrics.avgDuration, subtext: 'Latency baseline', color: 'text-muted-foreground' },
        { label: 'Avg Tokens', value: metrics.avgTokens, subtext: 'Context usage', color: 'text-amber-500' },
        { label: 'Lint Issues', value: metrics.totalLint, subtext: 'Total violations', color: 'text-red-500' },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-body">
            {cards.map((card, i) => (
                <Card key={i} className="p-4 bg-card border-border">
                    <p className="font-bold uppercase tracking-widest text-muted-foreground mb-1 truncate text-xs">{card.label}</p>
                    <p className={`text-header font-black tracking-tight ${card.color}`}>{card.value}</p>
                    <p className="text-muted-foreground/50 mt-1 font-medium italic text-xs">{card.subtext}</p>
                </Card>
            ))}
        </div>
    );
}