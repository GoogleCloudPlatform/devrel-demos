'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus, FileText, Lock } from 'lucide-react';
import LockToggle from '@/components/LockToggle';
import { toggleTemplateLock } from '@/app/api/api';

interface Template {
    id: string;
    name: string;
    description: string;
    alt_count?: number;
    scen_count?: number;
    alternatives?: string[];
    reps?: number;
    is_locked?: boolean;
}

export default function TemplatesPage() {
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingAll, setDeletingAll] = useState(false);

    useEffect(() => {
        fetch('/api/templates')
            .then(res => res.json())
            .then(data => {
                if (Array.isArray(data)) {
                    setTemplates(data);
                }
                setLoading(false);
            })
            .catch(err => {
                console.error(err);
                setLoading(false);
            });
    }, []);

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete template "${id}"?`)) return;

        try {
            const res = await fetch(`/api/templates/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success('Template deleted successfully');
                setTemplates(prev => prev.filter(t => t.id !== id));
            } else {
                toast.error('Failed to delete template');
            }
        } catch (err) {
            console.error(err);
            toast.error('Error deleting template');
        }
    };

    const handleDeleteAll = async () => {
        if (!confirm("⚠️ WARNING: This will delete ALL templates. This action cannot be undone.")) return;
        if (!confirm("Are you really sure?")) return;

        setDeletingAll(true);
        try {
            const res = await fetch('/api/templates/delete-all', { method: 'DELETE' });
            if (res.ok) {
                toast.success('All templates deleted successfully');
                setTemplates([]);
            } else {
                toast.error('Failed to delete all templates');
            }
        } catch (err) {
            console.error(err);
            toast.error('Error deleting templates');
        } finally {
            setDeletingAll(false);
        }
    };

    return (
        <div className="p-6 space-y-6">
            <header className="flex justify-between items-center pb-6 border-b border-border">
                <div>
                    <h1 className="text-title">Templates</h1>
                    <p className="text-body mt-1 font-medium">Experiment configurations.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deletingAll}>
                        Delete All
                    </Button>
                    <Link href="/templates/new">
                        <Button variant="default" size="sm">
                            <Plus className="mr-2 h-4 w-4" /> Create
                        </Button>
                    </Link>
                </div>
            </header>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-48 bg-card rounded-md border border-border"></div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {templates.map((template) => (
                        <Link href={`/templates/${template.id}`} key={template.id} className="block group">
                            <Card className={`h-full p-6 hover:border-muted transition-colors flex flex-col justify-between ${template.is_locked ? 'border-2 border-amber-500' : 'border border-border'}`}>
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center text-title text-muted-foreground group-hover:text-foreground transition-colors">
                                                📝
                                            </div>
                                            <div>
                                                <h3 className="text-header capitalize group-hover:text-primary transition-colors">
                                                    {template.name}
                                                </h3>
                                                <p className="text-body font-mono opacity-50 mt-1">ID: {template.id}</p>
                                            </div>
                                        </div>
                                        <div className="flex gap-1 items-center">
                                            <LockToggle
                                                locked={template.is_locked || false}
                                                onToggle={async (locked) => {
                                                    try {
                                                        await toggleTemplateLock(template.id, locked);
                                                        setTemplates(prev => prev.map(t => t.id === template.id ? { ...t, is_locked: locked } : t));
                                                        return true;
                                                    } catch (err) {
                                                        console.error(err);
                                                        return false;
                                                    }
                                                }}
                                            />
                                            <button
                                                onClick={(e) => handleDelete(e, template.id)}
                                                disabled={template.is_locked}
                                                className={`p-2 text-body text-muted-foreground hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity ${template.is_locked ? "cursor-not-allowed opacity-30" : ""}`}
                                                title={template.is_locked ? "Locked" : "Delete"}
                                            >
                                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                            </button>
                                        </div>
                                    </div>

                                    <p className="text-body text-muted-foreground line-clamp-2 mb-4 h-11">
                                        {template.description || "No description provided."}
                                    </p>

                                    <div className="mb-6 space-y-2 flex-1">
                                        <div className="text-body font-mono text-sm">
                                            <span className="font-bold text-muted-foreground mr-2 block mb-1 uppercase tracking-tighter">Alternatives:</span>
                                            <span className="text-foreground opacity-70 line-clamp-2 leading-relaxed">
                                                {template.alternatives?.join(', ') || "No alternatives defined"}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2 mt-4 pt-0">
                                    <span className="px-3 py-1 rounded-full text-mono font-bold text-xs uppercase tracking-wider border bg-blue-500/10 text-blue-400 border-blue-500/20">
                                        {template.alt_count} Alternatives
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-mono font-bold text-xs uppercase tracking-wider border bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                                        {template.scen_count} Scenarios
                                    </span>
                                    <span className="px-3 py-1 rounded-full text-mono font-bold text-xs uppercase tracking-wider border bg-amber-500/10 text-amber-400 border-amber-500/20">
                                        {template.reps} Repetitions
                                    </span>
                                </div>
                            </Card>
                        </Link>
                    ))}
                    {templates.length === 0 && (
                        <div className="col-span-2 text-center py-12 text-body opacity-50 italic border border-dashed border-border rounded">
                            No templates found. <Link href="/templates/new" className="text-primary hover:underline font-bold not-italic">Create one</Link>.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
