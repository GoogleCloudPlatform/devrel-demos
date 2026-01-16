'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Trash2, Plus, FlaskConical } from 'lucide-react';

interface Scenario {

    id: string;
    name: string;
    description: string;
    task?: string;
    github_issue?: string;
    validation?: any[];
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

    const handleDuplicate = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();

        setLoading(true); // Show global loading state briefly or use local state

        try {
            // 1. Fetch original
            const res = await fetch(`/api/scenarios/${id}`);
            if (!res.ok) throw new Error("Failed to fetch original");
            const original = await res.json();

            // 2. Prepare Payload (remove ID, update Name)
            // Note: We need to match the Shape expected by POST /api/scenarios
            // The API expects FormData for file uploads, which makes strict cloning hard if files are involved.
            // Ideally backend supports duplication, but here is a best-effort frontend duplication.

            const formData = new FormData();
            formData.append('name', `Copy of ${original.name}`);
            formData.append('description', original.description || "");

            if (original.validation) {
                formData.append('validation', JSON.stringify(original.validation));
            }
            if (original.env) {
                formData.append('env', JSON.stringify(original.env));
            }
            if (original.task) {
                formData.append('prompt', original.task); // API expects 'prompt' or 'task' depending on update logic, create uses 'prompt'
            }
            if (original.github_issue) {
                formData.append('github_issue', original.github_issue);
            }

            // Assets: This is tricky. 
            // If it's Git, we can copy. 
            // If it's local files, we can't easily re-upload them without re-downloading blobs.
            // For now, let's support Git and "Create" (file content) assets. 
            // Existing folder assets might fail to copy correctly without backend support.

            if (original.assets && original.assets.length > 0) {
                const asset = original.assets[0];
                if (asset.type === 'git') {
                    formData.append('asset_type', 'git');
                    formData.append('git_url', asset.source);
                    formData.append('git_ref', asset.ref || "");
                } else if (asset.type === 'file' && asset.content) {
                    formData.append('asset_type', 'create');
                    formData.append('file_name', asset.destination);
                    formData.append('file_content', asset.content);
                } else {
                    // Fallback/Warning for unsupported asset duplication
                    // We submit 'none' to avoid errors, user must re-upload.
                    formData.append('asset_type', 'none');
                    toast.warning("Asset copying not fully supported for this type. Please re-upload assets.");
                }
            } else {
                formData.append('asset_type', 'none');
            }

            // 3. Create Copy
            const createRes = await fetch('/api/scenarios', {
                method: 'POST',
                body: formData
            });

            if (createRes.ok) {
                toast.success("Scenario duplicated!");
                // Refresh list
                const newScenario = await createRes.json();
                // If API returns the object, add it. If not, re-fetch all.
                // Assuming re-fetch for safety:
                const listRes = await fetch('/api/scenarios');
                const listData = await listRes.json();
                setScenarios(listData);
            } else {
                toast.error("Failed to duplicate scenario");
            }

        } catch (e) {
            console.error(e);
            toast.error("Error duplicating scenario");
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteAll = async () => {
        if (!confirm("⚠️ WARNING: This will delete ALL scenarios. This action cannot be undone.")) return;
        if (!confirm("Are you really sure?")) return;

        setDeletingAll(true);
        try {
            const res = await fetch('/api/scenarios/delete-all', { method: 'DELETE' });
            if (res.ok) {
                toast.success('All scenarios deleted successfully');
                setScenarios([]);
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

    return (
        <div className="p-6 space-y-6">
            <header className="flex justify-between items-center pb-6 border-b border-[#27272a]">
                <div>
                    <h1 className="text-title">Scenarios</h1>
                    <p className="text-body mt-1 font-medium">Standardized coding tasks.</p>
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
                        <div key={i} className="h-48 bg-[#121214] rounded-md border border-[#27272a]"></div>
                    ))}
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {scenarios.map((scenario) => (
                        <Link href={`/scenarios/${scenario.id}`} key={scenario.id} className="block group">
                            <Card className="h-full p-6 hover:border-[#3f3f46] transition-colors border border-[#27272a] flex flex-col justify-between">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-4">
                                            <div className="w-12 h-12 rounded-lg bg-[#27272a] flex items-center justify-center text-title text-[#a1a1aa] group-hover:text-[#f4f4f5] transition-colors">
                                                🧪
                                            </div>
                                            <div>
                                                <h3 className="text-header capitalize group-hover:text-[#6366f1] transition-colors">
                                                    {scenario.name}
                                                </h3>
                                                <p className="text-body font-mono opacity-50 mt-1">ID: {scenario.id}</p>
                                            </div>
                                        </div>
                                        <div className="flex gap-1">
                                            <button
                                                onClick={(e) => handleDuplicate(e, scenario.id)}
                                                className="p-2 text-body text-[#52525b] hover:text-[#6366f1] opacity-0 group-hover:opacity-100 transition-opacity"
                                                title="Duplicate"
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" /></svg>
                                            </button>
                                            <button
                                                onClick={(e) => handleDelete(e, scenario.id)}
                                                className="p-2 text-body text-[#52525b] hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                                                title="Delete"
                                            >
                                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                                            </button>
                                        </div>
                                    </div>

                                    <p className="text-body text-[#a1a1aa] line-clamp-2 mb-4 h-11">
                                        {scenario.description || "No description provided."}
                                    </p>

                                    <div className="mb-6 space-y-2 flex-1">
                                        {scenario.github_issue ? (
                                            <div className="text-body font-mono truncate">
                                                <span className="font-bold text-[#52525b] mr-2">GITHUB:</span>
                                                <span className="text-[#6366f1]">{scenario.github_issue}</span>
                                            </div>
                                        ) : (
                                            <div className="text-body font-mono">
                                                <span className="font-bold text-[#52525b] mr-2 block mb-1">PROMPT:</span>
                                                <span className="text-[#f4f4f5] opacity-70 line-clamp-4 leading-relaxed">
                                                    {scenario.task || "No prompt defined"}
                                                </span>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div className="flex flex-wrap gap-2 mt-4 pt-0">
                                    {scenario.validation?.map((v, i) => (
                                        <span key={i} className={`px-3 py-1 rounded-full text-mono font-bold text-xs uppercase tracking-wider border ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                            v.type === 'lint' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                                'bg-blue-500/10 text-blue-400 border-blue-500/20'
                                            }`}>
                                            {v.type === 'test' ? `Test >= ${v.min_coverage ?? 0}%` :
                                                v.type === 'lint' ? `Lint <= ${v.max_issues ?? 0}` :
                                                    v.type === 'command' ? `Cmd (Exit ${v.expected_exit_code ?? 0})` : v.type}
                                        </span>

                                    ))}
                                    {(!scenario.validation || scenario.validation.length === 0) && (
                                        <span className="text-mono opacity-30 italic">No validation</span>
                                    )}
                                </div>
                            </Card>
                        </Link>
                    ))}
                    {scenarios.length === 0 && (
                        <div className="col-span-2 text-center py-12 text-body opacity-50 italic border border-dashed border-[#27272a] rounded">
                            No scenarios found. <Link href="/scenarios/new" className="text-[#6366f1] hover:underline font-bold not-italic">Create one</Link>.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
