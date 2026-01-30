"use client";

import { useState, useEffect } from "react";
import { getScenarios, getTemplates } from "@/lib/api";
import ExperimentForm from "@/components/ExperimentForm";
import { PageHeader } from "@/components/ui/page-header";
import { Loader2 } from "lucide-react";

export default function NewExperimentPage() {
    const [data, setData] = useState<{ templates: any[], scenarios: any[] } | null>(null);

    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [templates, scenarios] = await Promise.all([
                    getTemplates(),
                    getScenarios()
                ]);
                setData({ templates, scenarios });
            } catch (err: any) {
                console.error("Failed to load experiment data:", err);
                setError(err.message || "Failed to load templates or scenarios.");
            }
        };
        fetchData();
    }, []);

    if (error) {
        return (
            <div className="p-20 text-center space-y-4">
                <h2 className="text-xl font-bold text-destructive">Failed to Load Content</h2>
                <p className="text-muted-foreground">{error}</p>
                <p className="text-sm">Please ensure the server is running and templates are properly configured.</p>
            </div>
        );
    }

    if (!data) return <div className="p-20 flex justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Launch Experiment"
                description="Initialize a new agent benchmarking session."
                backHref="/experiments"
            />

            <ExperimentForm templates={data.templates} scenarios={data.scenarios} />
        </div>
    );
}