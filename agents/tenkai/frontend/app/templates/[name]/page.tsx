'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useParams } from 'next/navigation';
import TemplateForm from '@/components/TemplateForm';

export default function TemplateEditor() {
    const params = useParams();
    const router = useRouter();
    const name = params.name as string;

    const [content, setContent] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetch(`/api/templates/${name}/config`)
            .then(res => {
                if (!res.ok) throw new Error('Failed to load config');
                return res.json();
            })
            .then(data => {
                setContent(data.content);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, [name]);

    const handleSave = async (newContent: string) => {
        const res = await fetch(`/api/templates/${name}/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: newContent }),
        });

        if (!res.ok) throw new Error('Failed to save config');

        alert('Configuration saved successfully!');
        router.refresh();
    };

    if (loading) return <div className="p-10 text-center text-zinc-500 animate-pulse">Loading template...</div>;
    if (error) return <div className="p-10 text-center text-red-500">Error: {error}</div>;

    return (
        <div className="p-10 space-y-8 animate-in fade-in duration-500 max-w-7xl mx-auto min-h-screen flex flex-col">
            <header className="flex justify-between items-start border-b border-white/5 pb-8">
                <div className="flex items-center gap-4">
                    <button
                        onClick={async () => {
                            if (!confirm(`Are you sure you want to delete template "${name}"? This action cannot be undone.`)) return;

                            try {
                                const res = await fetch(`/api/templates/${name}`, { method: 'DELETE' });
                                if (!res.ok) throw new Error('Failed to delete template');
                                router.push('/templates');
                            } catch (e: any) {
                                alert(`Error: ${e.message}`);
                            }
                        }}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-500 hover:text-red-400 font-bold py-2 px-4 rounded-lg transition-colors border border-red-500/20 uppercase text-xs tracking-widest"
                    >
                        Delete Template
                    </button>
                    <Link href="/templates" className="text-xs font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors">← Back to Templates</Link>
                </div>
            </header>

            <div className="border-b border-white/5 pb-8 -mt-4 mb-8">
                <h1 className="text-4xl font-bold tracking-tight mt-2 capitalize">{name.replace(/-/g, ' ')}</h1>
                <p className="text-zinc-400 mt-2 text-base font-mono">experiments/templates/{name}/config.yaml</p>
            </div>

            <div className="flex-1">
                <TemplateForm initialContent={content} onSubmit={handleSave} name={name} />
            </div>

            <p className="text-zinc-500 text-sm text-center font-bold uppercase tracking-widest pt-10">
                Changes apply only to new experiments.
            </p>
        </div>
    );
}
