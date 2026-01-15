"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Loader2, Plus, Lock, Unlock, Edit, Copy } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { getTemplates, Template, lockTemplate } from "../api/api";
import { useRouter } from "next/navigation";

export default function TemplatesPage() {
    const router = useRouter();
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingAll, setDeletingAll] = useState(false);

    const fetchTemplates = async () => {
        setLoading(true);
        try {
            if (typeof window === 'undefined') return;
            const data = await getTemplates();
            setTemplates(data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load templates");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchTemplates();
    }, []);

    const handleDeleteAll = async () => {
        if (!confirm("Delete ALL templates?")) return;
        setDeletingAll(true);
        try {
            const res = await fetch('/api/templates/delete-all', { method: 'DELETE' });
            if (res.ok) {
                toast.success("All templates deleted");
                fetchTemplates();
            } else {
                toast.error("Failed to delete templates");
            }
        } catch (e) {
            toast.error("Error deleting templates");
        } finally {
            setDeletingAll(false);
        }
    };

    const handleToggleLock = async (e: React.MouseEvent, id: string, currentLocked: boolean) => {
        e.preventDefault();
        e.stopPropagation();

        try {
            // Check if ID is number or string. interface says string. api says string|number.
            const res = await lockTemplate(id, !currentLocked);
            if (res) {
                setTemplates(prev => prev.map(t => t.id === id ? { ...t, locked: !currentLocked } : t));
                toast.success(currentLocked ? "Unlocked" : "Locked");
            }
        } catch (err) {
            console.error(err);
            toast.error("Failed to toggle lock");
        }
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Experiment Templates"
                description="Reusable configurations for running experiments."
                actions={
                    <div className="flex gap-2">
                        <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deletingAll}>
                            Delete All
                        </Button>
                        <Link href="/templates/view?id=new">
                            <Button>
                                <Plus className="w-4 h-4 mr-2" />
                                New Template
                            </Button>
                        </Link>
                    </div>
                }
            />

            {loading ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {templates.map((template) => (
                        <Link href={`/templates/view?id=${template.id}`} key={template.id} className="block group">
                            <Card className="h-full p-6 hover:border-primary/50 transition-colors border border-border flex flex-col justify-between bg-card text-card-foreground">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg 
                                                ${template.locked ? 'bg-amber-500/10 text-amber-500' : 'bg-primary/10 text-primary'}`}>
                                                {template.locked ? <Lock className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-lg group-hover:text-primary transition-colors">{template.name}</h3>
                                                <p className="text-xs font-mono text-muted-foreground">{template.id}</p>
                                            </div>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={(e) => handleToggleLock(e, template.id, template.locked)}
                                            className={template.locked ? "text-amber-500 hover:text-amber-400" : "text-zinc-500 hover:text-zinc-400"}
                                        >
                                            {template.locked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                                        </Button>
                                    </div>
                                    <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                                        {template.description || "No description provided."}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 pt-4 border-t border-border mt-4">
                                    {/* Additional info badges */}
                                </div>
                            </Card>
                        </Link>
                    ))}
                    {templates.length === 0 && (
                        <div className="col-span-2 text-center p-12 text-muted-foreground bg-card/50 rounded-xl border border-border border-dashed">
                            No templates found. Create one to get started.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
