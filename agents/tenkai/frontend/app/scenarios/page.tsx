'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus, FlaskConical, Lock, LockOpen } from 'lucide-react';
import { lockScenario } from '@/app/api/api';

interface Scenario {

    id: string;
    name: string;
    description: string;
    task?: string;
    github_issue?: string;
    validation?: any[];
    locked?: boolean;
}

export default function ScenariosPage() {
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingAll, setDeletingAll] = useState(false);

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

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();

        const scenario = scenarios.find(s => s.id === id);
        if (scenario?.locked) {
            toast.error("Scenario is locked. Unlock it first.");
            return;
        }

        if (!confirm('Are you sure you want to delete this scenario? This action cannot be undone.')) return;

        try {
            const res = await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success('Scenario deleted successfully');
                setScenarios(prev => prev.filter(s => s.id !== id));
            } else {
                toast.error('Failed to delete scenario');
            }
        } catch (err) {
            console.error(err);
            toast.error('Error deleting scenario');
        }
    };

    const handleDeleteAll = async () => {
        if (!confirm("⚠️ WARNING: This will delete ALL UNLOCKED scenarios. This action cannot be undone.")) return;
        if (!confirm("Are you really sure?")) return;

        setDeletingAll(true);
        try {
            const res = await fetch('/api/scenarios/delete-all', { method: 'DELETE' });
            if (res.ok) {
                toast.success('All unlocked scenarios deleted successfully');
                // Reload list
                setLoading(true);
                fetch('/api/scenarios')
                    .then(res => res.json())
                    .then(data => {
                        setScenarios(data);
                        setLoading(false);
                    });
            } else {
                toast.error('Failed to delete all scenarios');
            }
        } catch (err) {
            console.error(err);
            toast.error('Error deleting scenarios');
        } finally {
            setDeletingAll(false);
        }
    };

    const handleToggleLock = async (e: React.MouseEvent, id: string, currentLocked: boolean) => {
        e.preventDefault();
        e.stopPropagation();

        try {
            const res = await lockScenario(id, !currentLocked);
            if (res) {
                setScenarios(prev => prev.map(s => s.id === id ? { ...s, locked: !currentLocked } : s));
                toast.success(currentLocked ? "Unlocked" : "Locked");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to toggle lock");
        }
    };

    return (
        <div className="p-6 space-y-6">
            <header className="flex justify-between items-center pb-6 border-b border-border">
                <div>
                    <h1 className="text-title text-foreground">Scenarios</h1>
                    <p className="text-muted-foreground mt-1 font-medium">Standardized coding tasks.</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deletingAll}>
                        Delete All
                    </Button>
                    <Link href="/scenarios/new">
                        <Button variant="default" size="sm">
                            <Plus className="mr-2 h-4 w-4" /> Create
                        </Button>
                    </Link>
                </div>
            </header>

            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
                    {[1, 2, 3, 4].map(i => (
                        <div key={i} className="h-48 bg-muted rounded-md border border-border"></div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {scenarios.map((scenario) => (
                        <Link href={`/scenarios/${scenario.id}`} key={scenario.id} className="block group">
                            <Card className="h-full p-6 hover:border-primary/50 transition-colors border border-border flex flex-col justify-between bg-card">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center text-title text-muted-foreground group-hover:text-foreground transition-colors">
                                                🧪
                                            </div>
                                            <div>
                                                <h3 className="text-header capitalize group-hover:text-primary transition-colors text-foreground">
                                                    {scenario.name}
                                                </h3>
                                                <p className="text-muted-foreground font-mono opacity-60 mt-1 text-xs">ID: {scenario.id}</p>
                                            </div>
                                        </div>
                                        <button
                                            onClick={(e) => handleToggleLock(e, scenario.id, !!scenario.locked)}
                                            className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                                            title={scenario.locked ? "Unlock" : "Lock"}
                                        >
                                            {scenario.locked ? (
                                                <Lock className="w-5 h-5 text-amber-500" />
                                            ) : (
                                                <LockOpen className="w-5 h-5 opacity-50 hover:opacity-100" />
                                            )}
                                        </button>
                                        <button
                                            onClick={(e) => handleDelete(e, scenario.id)}
                                            className={`p-2 transition-opacity ${scenario.locked ? 'text-muted-foreground opacity-30 cursor-not-allowed' : 'text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100'}`}
                                            title={scenario.locked ? "Locked" : "Delete"}
                                            disabled={!!scenario.locked}
                                        >
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                        </button>
                                    </div>

                                    <p className="text-sm text-muted-foreground line-clamp-2 mb-4 h-11 leading-relaxed">
                                        {scenario.description || "No description provided."}
                                    </p>

                                    <div className="mb-6 space-y-2 flex-1">
                                        {scenario.github_issue ? (
                                            <div className="text-xs font-mono truncate">
                                                <span className="font-bold text-muted-foreground mr-2">GITHUB:</span>
                                                <span className="text-primary">{scenario.github_issue}</span>
                                            </div>
                                        ) : (
                                            <div className="text-xs font-mono">
                                                <span className="font-bold text-muted-foreground mr-2 block mb-1 uppercase tracking-widest">PROMPT:</span>
                                                <span className="text-foreground/70 line-clamp-4 leading-relaxed italic">
                                                    {scenario.task || "No prompt defined"}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2 mt-4 pt-0">
                                    {scenario.validation?.map((v, i) => (
                                        <span key={i} className={`px-3 py-1 rounded-full text-mono font-bold text-[10px] uppercase tracking-wider border ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20' :
                                            v.type === 'lint' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20' :
                                                'bg-primary/10 text-primary border-primary/20'
                                            }`}>
                                            {v.type === 'test' ? `Test >= ${v.min_coverage ?? 0}%` :
                                                v.type === 'lint' ? `Lint <= ${v.max_issues ?? 0}` :
                                                    v.type === 'command' ? `Cmd (Exit ${v.expected_exit_code ?? 0})` : v.type}
                                        </span>
                                    ))}
                                    {(!scenario.validation || scenario.validation.length === 0) && (
                                        <span className="text-mono opacity-30 italic text-[10px] text-muted-foreground">No validation</span>
                                    )}
                                </div>
                            </Card>
                        </Link>
                    ))}
                    {scenarios.length === 0 && (
                        <div className="col-span-2 text-center py-12 text-muted-foreground opacity-50 italic border border-dashed border-border rounded">
                            No scenarios found. <Link href="/scenarios/new" className="text-primary hover:underline font-bold not-italic">Create one</Link>.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
