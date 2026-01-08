import { Card } from "@/components/ui/card";

export default function MetricsOverview({ metrics }: { metrics: any }) {
    if (!metrics) return null;

    const cards = [
        { label: 'Total Executions', value: metrics.total, subtext: 'Baseline reps', color: 'text-white' },
        { label: 'Successful Runs', value: metrics.successful, subtext: 'Verified results', color: 'text-emerald-400' },
        { label: 'Avg Success Rate', value: metrics.successRate, subtext: 'Benchmark mean', color: 'text-indigo-400' },
        { label: 'Avg Duration', value: metrics.avgDuration, subtext: 'Latency baseline', color: 'text-zinc-400' },
        { label: 'Avg Tokens', value: metrics.avgTokens, subtext: 'Context usage', color: 'text-amber-400' },
        { label: 'Lint Issues', value: metrics.totalLint, subtext: 'Total violations', color: 'text-red-400' },
    ];

    return (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 text-body">
            {cards.map((card, i) => (
                <Card key={i} className="p-4 bg-[#0c0c0e]">
                    <p className="font-bold uppercase tracking-widest text-[#52525b] mb-1 truncate">{card.label}</p>
                    <p className={`text-header font-black tracking-tight ${card.color}`}>{card.value}</p>
                    <p className="opacity-50 mt-1 font-medium italic">{card.subtext}</p>
                </Card>
            ))}
        </div>
    );
}