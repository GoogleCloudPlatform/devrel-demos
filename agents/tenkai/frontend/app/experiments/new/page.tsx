"use client";

import { useEffect, useState } from "react";
import { getScenarios, getTemplates, Scenario, Template } from "../../api/api";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import ExperimentForm from "@/components/ExperimentForm";

export default function NewExperimentPage() {
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            // Only run in browser
            if (typeof window === 'undefined') return;
            try {
                const [s, t] = await Promise.all([getScenarios(), getTemplates()]);
                setScenarios(s);
                setTemplates(t);
            } catch (e) {
                console.error(e);
                toast.error("Failed to load options");
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, []);

    if (loading) return <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin text-muted-foreground" /></div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="New Experiment"
                description="Configure and launch a new agent evaluation run."
                backHref="/experiments"
                backLabel="Back to Experiments"
            />

            <ExperimentForm templates={templates} scenarios={scenarios} />
        </div>
    );
}