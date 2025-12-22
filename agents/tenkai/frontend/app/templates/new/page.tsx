'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import yaml from 'js-yaml';

export default function NewTemplate() {
    const router = useRouter();
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const res = await fetch('/api/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description }),
            });

            if (!res.ok) {
                const data = await res.json();
                throw new Error(data.error || 'Failed to create template');
            }

            const data = await res.json();
            router.push(`/templates/${data.name}`);
        } catch (err: any) {
            setError(err.message);
            setLoading(false);
        }
    };

    return (
        <div className="p-10 space-y-8 animate-in fade-in duration-500 max-w-2xl mx-auto min-h-screen flex flex-col justify-center">
            <header className="mb-8">
                <Link href="/templates" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Back to Templates</Link>
                <h1 className="text-4xl font-bold tracking-tight mt-4">Create New Template</h1>
                <p className="text-zinc-400 mt-2 text-lg">Initialize a new experiment blueprint.</p>
            </header>

            <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                    <label className="block text-sm font-bold text-zinc-300 mb-2 uppercase tracking-wide">Template Name</label>
                    <input
                        type="text"
                        required
                        placeholder="e.g. prompt-optimization-study"
                        className="w-full bg-black border border-zinc-800 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all font-mono text-base"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                    />
                    <p className="text-xs text-zinc-500 mt-2">Will be converted to kebab-case: <span className="font-mono text-zinc-400">{name.toLowerCase().replace(/[^a-z0-9-_]/g, '-')}</span></p>
                </div>

                <div>
                    <label className="block text-sm font-bold text-zinc-300 mb-2 uppercase tracking-wide">Description</label>
                    <textarea
                        className="w-full bg-black border border-zinc-800 rounded-lg px-4 py-3 text-white focus:border-blue-500 outline-none transition-all h-32 resize-none"
                        placeholder="Briefly describe the goal of this experiment series..."
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                    />
                </div>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl text-sm font-bold">
                        Error: {error}
                    </div>
                )}

                <button
                    type="submit"
                    disabled={loading || !name}
                    className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 px-6 rounded-lg shadow-lg shadow-blue-500/20 transition-all border border-blue-400/20 uppercase text-sm tracking-widest disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {loading ? 'Creating...' : 'Create Template'}
                </button>
            </form>
        </div>
    );
}
