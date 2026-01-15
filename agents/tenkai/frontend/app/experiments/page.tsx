"use client";

import { ExperimentRecord, getExperiments } from "../api/api";
import { PageHeader } from "@/components/ui/page-header";
import ExperimentsTable from "@/components/experiments/ExperimentsTable";
import { useEffect, useState } from "react";
import { Loader2, Plus } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";

export default function ExperimentsPage() {
    const [experiments, setExperiments] = useState<ExperimentRecord[]>([]);
    const [loading, setLoading] = useState(true);

    const loadExperiments = async () => {
        setLoading(true);
        try {
            // Check if we are in browser
            if (typeof window === 'undefined') return;
            const data = await getExperiments();
            setExperiments(data);
        } catch (error) {
            console.error("Failed to fetch experiments", error);
            toast.error("Failed to load experiments");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadExperiments();
    }, []);

    const handleRefresh = () => {
        loadExperiments();
    };

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Experiments"
                description="Manage and monitor agent evaluation experiments."
                actions={
                    <Link href="/experiments/new">
                        <Button size="sm">
                            <Plus className="mr-2 h-4 w-4" /> New Experiment
                        </Button>
                    </Link>
                }
            />

            {loading ? (
                <div className="flex justify-center p-12">
                    <Loader2 className="w-8 h-8 animate-spin text-zinc-500" />
                </div>
            ) : (
                <ExperimentsTable experiments={experiments} />
            )}
        </div>
    );
}
