'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface Scenario {
    id: string;
    name: string;
    description: string;
}

export default function ScenariosPage() {
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetch('/api/scenarios')
            .then(res => res.json())
            .then(data => {
                setScenarios(data);
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    return (
        <div className="p-10 space-y-10 animate-in fade-in duration-500 max-w-7xl mx-auto">
            <header className="flex justify-between items-end border-b border-white/5 pb-8">
                <div>
                    <Link href="/" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Dashboard</Link>
                    <h1 className="text-4xl font-bold tracking-tight mt-2">Scenarios</h1>
                    <p className="text-zinc-400 mt-2">Browse available coding task scenarios.</p>
                </div>
            </header>

            {loading ? (
                <div className="text-zinc-500">Loading scenarios...</div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {scenarios.map((scenario) => (
                        <Link href={`/scenarios/${scenario.id}`} key={scenario.id}>
                            <div className="glass p-6 rounded-2xl border border-white/5 hover:bg-white/[0.02] hover:border-blue-500/30 transition-all cursor-pointer group">
                                <div className="flex justify-between items-start mb-4">
                                    <span className="text-2xl">🧪</span>
                                    <span className="text-zinc-500 group-hover:text-blue-400 transition-colors">→</span>
                                </div>
                                <h3 className="font-bold text-lg text-gray-200 capitalize group-hover:text-white transition-colors">
                                    {scenario.name}
                                </h3>
                                {scenario.description && (
                                    <p className="text-sm text-zinc-500 mt-2 line-clamp-2">
                                        {scenario.description}
                                    </p>
                                )}
                                <div className="mt-4 pt-4 border-t border-white/5 flex justify-between items-center">
                                    <span className="text-xs text-zinc-600 font-mono">{scenario.id}</span>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
