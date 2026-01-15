"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Loader2, Plus, Lock, Unlock, Trash2, Edit } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import { getScenarios, Scenario, deleteScenario, lockScenario } from "../api/api";
import { useRouter } from "next/navigation";

export default function ScenariosPage() {
    const router = useRouter();
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [loading, setLoading] = useState(true);
    const [deletingAll, setDeletingAll] = useState(false);

    const fetchScenarios = async () => {
        setLoading(true);
        try {
            if (typeof window === 'undefined') return;
            const data = await getScenarios();
            setScenarios(data);
        } catch (e) {
            console.error(e);
            toast.error("Failed to load scenarios");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchScenarios();
    }, []);

    const handleCreate = async () => {
        // For simplicity, redirect to new? Or use modal?
        // Current implementation seems to rely on form elsewhere or maybe this page had a form?
        // Seeing previous file, it was just a list.
        router.push('/scenarios/view?id=new'); // Assuming we handle new via ID or a separate route
    };

    const handleDeleteAll = async () => {
        if (!confirm("Delete ALL scenarios? This is irreversible.")) return;
        setDeletingAll(true);
        try {
            const res = await fetch('/api/scenarios/delete-all', { method: 'DELETE' });
            if (res.ok) {
                toast.success("All scenarios deleted");
                fetchScenarios();
            } else {
                toast.error("Failed to delete scenarios");
            }
        } catch (e) {
            toast.error("Error deleting scenarios");
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
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Scenarios"
                description="Define coding tasks and validation rules."
                actions={
                    <div className="flex gap-2">
                        <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deletingAll}>
                            Delete All
                        </Button>
                        <Link href="/scenarios/view?id=new">
                            <Button>
                                <Plus className="w-4 h-4 mr-2" />
                                New Scenario
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
                    {scenarios.map((scenario) => (
                        <Link href={`/scenarios/view?id=${scenario.id}`} key={scenario.id} className="block group">
                            <Card className="h-full p-6 hover:border-primary/50 transition-colors border border-border flex flex-col justify-between bg-card text-card-foreground">
                                <div>
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="flex items-center gap-3">
                                            <div className={`p-2 rounded-lg 
                                                ${scenario.locked ? 'bg-amber-500/10 text-amber-500' : 'bg-primary/10 text-primary'}`}>
                                                {scenario.locked ? <Lock className="w-4 h-4" /> : <Edit className="w-4 h-4" />}
                                            </div>
                                            <div>
                                                <h3 className="font-bold text-lg group-hover:text-primary transition-colors">{scenario.name}</h3>
                                                <p className="text-xs font-mono text-muted-foreground">{scenario.id}</p>
                                            </div>
                                        </div>
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            onClick={(e) => handleToggleLock(e, scenario.id, scenario.locked)}
                                            className={scenario.locked ? "text-amber-500 hover:text-amber-400" : "text-zinc-500 hover:text-zinc-400"}
                                        >
                                            {scenario.locked ? <Lock className="w-4 h-4" /> : <Unlock className="w-4 h-4" />}
                                        </Button>
                                    </div>
                                    <p className="text-sm text-muted-foreground line-clamp-3 mb-4">
                                        {scenario.description || "No description provided."}
                                    </p>
                                </div>
                                <div className="flex items-center gap-2 pt-4 border-t border-border mt-4">
                                    <span className="text-xs font-mono px-2 py-1 bg-secondary rounded text-secondary-foreground border border-border/50">
                                        Task: {scenario.task ? "Defined" : "Empty"}
                                    </span>
                                    {/* Add more badges if needed */}
                                </div>
                            </Card>
                        </Link>
                    ))}
                    {scenarios.length === 0 && (
                        <div className="col-span-2 text-center p-12 text-muted-foreground bg-card/50 rounded-xl border border-border border-dashed">
                            No scenarios found. Create one to get started.
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
