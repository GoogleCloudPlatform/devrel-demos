'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';

interface ScenarioDetail {
    id: string;
    name: string;
    description: string;
    raw: string;
}

export default function ScenarioDetailPage() {
    const params = useParams();
    const id = params.id as string;
    const [scenario, setScenario] = useState<ScenarioDetail | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!id) return;
        fetch(`/api/scenarios/${id}`)
            .then(res => res.json())
            .then(data => {
                setScenario(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, [id]);

    if (loading) {
        return <div className="p-10 text-zinc-500">Loading scenario details...</div>;
    }

    if (!scenario) {
        return <div className="p-10 text-red-500">Scenario not found.</div>;
    }

    return (
        <div className="p-10 space-y-10 animate-in fade-in duration-500 max-w-7xl mx-auto">
            <header className="border-b border-white/5 pb-8">
                <Link href="/scenarios" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Back to Scenarios</Link>
                <div className="flex justify-between items-end mt-2">
                    <div>
                        <h1 className="text-4xl font-bold tracking-tight capitalize">{scenario.name}</h1>
                        <p className="text-zinc-400 mt-2">{scenario.description}</p>
                    </div>
                    <span className="text-xs bg-white/5 px-3 py-1 rounded-full font-mono text-zinc-400">{scenario.id}</span>
                </div>
            </header>

            <div className="space-y-6">
                <div className="glass p-6 rounded-2xl border border-white/5">
                    <h2 className="text-xl font-bold mb-4 flex items-center gap-2">
                        <span>📜</span> Definition (YAML)
                    </h2>
                    <div className="bg-[#0D1117] p-4 rounded-lg overflow-x-auto border border-white/5">
                        <pre className="text-sm font-mono text-zinc-300 leading-relaxed">
                            {scenario.raw}
                        </pre>
                    </div>
                </div>
            </div>
        </div>
    );
}

