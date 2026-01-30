"use client";

import React, { Suspense, useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Loader2 } from "lucide-react";
import { toggleScenarioLock } from "@/lib/api";
import LockToggle from "@/components/LockToggle";
import ScenarioForm from "@/components/ScenarioForm";

function ScenarioEditorContent({ id }: { id: string }) {
    const router = useRouter();

    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);
    const [isLocked, setIsLocked] = useState(false);
    const [scenarioData, setScenarioData] = useState<any>(null);

    useEffect(() => {
        if (!id) {
            setFetching(false);
            return;
        }

        const fetchScenario = async () => {
            try {
                const res = await fetch(`/api/scenarios/${id}`);
                if (!res.ok) throw new Error("Failed");
                const data = await res.json();
                setScenarioData(data);
                setIsLocked(data.is_locked || false);
            } catch (e) {
                console.error(e);
                toast.error("Failed to load scenario editor");
                router.push('/scenarios');
            } finally {
                setFetching(false);
            }
        };
        fetchScenario();
    }, [id, router]);

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this scenario? This cannot be undone.")) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Scenario deleted successfully");
                router.push('/scenarios');
                router.refresh();
            } else {
                toast.error("Failed to delete scenario");
            }
        } catch (e) {
            toast.error("Error deleting scenario");
        } finally {
            setLoading(false);
        }
    };

    const handleUpdate = async (formData: FormData) => {
        setLoading(true);
        try {
            const res = await fetch(`/api/scenarios/${id}`, {
                method: 'PUT',
                body: formData
            });

            if (res.ok) {
                toast.success("Scenario updated successfully");
                router.refresh();
            } else {
                toast.error("Failed to update scenario");
            }
        } catch (e) {
            toast.error("Error updating scenario");
        } finally {
            setLoading(false);
        }
    };

    if (fetching) return <div className="p-20 text-center text-body animate-pulse">Loading Workbench...</div>;
    if (!id) return <div className="p-20 text-center text-red-500">Missing Scenario ID</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Edit Scenario"
                description={`System ID: ${id}`}
                backHref="/scenarios"
                actions={
                    <>
                        <LockToggle
                            locked={isLocked}
                            onToggle={async (locked) => {
                                const success = await toggleScenarioLock(id, locked);
                                if (success) {
                                    setIsLocked(locked);
                                    return true;
                                }
                                return false;
                            }}
                        />
                        <Button variant="destructive" size="sm" onClick={handleDelete} disabled={loading || isLocked}>
                            Delete Scenario
                        </Button>
                    </>
                }
            />

            <ScenarioForm
                mode="edit"
                initialData={scenarioData}
                onSubmit={handleUpdate}
                isLoading={loading}
                isLocked={isLocked}
            />
        </div>
    );
}

export default function ClientScenarioEditor({ id }: { id: string }) {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ScenarioEditorContent id={id} />
        </Suspense>
    );
}
