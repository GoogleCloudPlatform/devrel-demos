"use client";

import React, { Suspense, useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import TemplateForm from "@/components/TemplateForm";
import { PageHeader } from "@/components/ui/page-header";
import { Loader2 } from "lucide-react";
import { ScenarioData, TemplateData } from "@/types/domain";

function TemplateEditorContent({ name }: { name: string }) {
    const router = useRouter();

    const [scenarios, setScenarios] = useState<ScenarioData[]>([]);
    const [initialData, setInitialData] = useState<TemplateData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (!name) {
            setLoading(false);
            return;
        }

        const loadData = async () => {
            try {
                const [scens, template] = await Promise.all([
                    fetch('/api/scenarios').then(res => res.json()),
                    fetch(`/api/templates/${name}/config`).then(res => res.json())
                ]);

                setScenarios(scens);
                setInitialData({
                    id: name,
                    name: template.name || name,
                    yaml_content: template.content,
                    description: template.description || "",
                    config: template.config || {
                        reps: 1,
                        concurrent: 1,
                        timeout: "",
                        experiment_control: "",
                        scenarios: [],
                        alternatives: []
                    }
                });

            } catch (e) {
                console.error(e);
                toast.error("Failed to load template editor");
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [name]);

    if (!name) return <div className="p-20 text-center text-red-500">Missing Template Name/ID</div>;
    if (loading) return <div className="p-20 text-center animate-pulse text-body">Loading Environment...</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Edit Template"
                description={`ID: ${initialData?.id}`}
                backHref="/templates"
            />

            <TemplateForm scenarios={scenarios} initialData={initialData} mode="edit" />
        </div>
    );
}

export default function TemplateEditorPage({ params }: { params: Promise<{ name: string }> }) {
    const { name } = use(params);
    
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <TemplateEditorContent name={name} />
        </Suspense>
    );
}