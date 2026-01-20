'use client';

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Plus } from "lucide-react";

import { toast } from "sonner";

export default function ExperimentsHeader() {
    const router = useRouter();
    const [deletingAll, setDeletingAll] = useState(false);

    const handleDeleteAll = async () => {
        if (!confirm("⚠️ WARNING: This will delete ALL experiments and their results permanently.\n\nThis action cannot be undone.")) return;
        if (!confirm("Are you really sure?")) return;

        setDeletingAll(true);
        try {
            const res = await fetch('/api/experiments', { method: 'DELETE' });
            if (res.ok) {
                toast.success("All experiments deleted successfully");
                router.refresh();
            } else {
                toast.error("Failed to delete all experiments");
            }
        } catch (e) {
            toast.error("Error deleting experiments");
        } finally {
            setDeletingAll(false);
        }
    };

    return (
        <header className="flex justify-between items-center pb-6 border-b border-border">
            <div>
                <h1 className="text-title">Experiments</h1>
                <p className="text-body mt-1 font-medium">Full history of agent benchmarking runs.</p>
            </div>
            <div className="flex gap-2">
                <Button variant="destructive" size="sm" onClick={handleDeleteAll} disabled={deletingAll}>
                    Delete All
                </Button>
                <Link href="/experiments/new">
                    <Button variant="default" size="sm">
                        <Plus className="mr-2 h-4 w-4" /> Create
                    </Button>
                </Link>
            </div>
        </header>
    );
}