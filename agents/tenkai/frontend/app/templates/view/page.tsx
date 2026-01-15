"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import TemplateForm from "@/components/TemplateForm";
import { PageHeader } from "@/components/ui/page-header";
import { Loader2 } from "lucide-react";

function TemplateEditorContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const name = searchParams.get('id'); // Using id param for name (or change to 'name')

    const [scenarios, setScenarios] = useState<any[]>([]);
    const [initialData, setInitialData] = useState<any>(null);
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
                    config: template.config || {}
                });

                // If config is not in response, try to parse it from content
                if (!template.config && template.content) {
                    try {
                        const yaml = require('js-yaml');
                        setInitialData((prev: any) => ({
                            ...prev,
                            config: yaml.load(template.content)
                        }));
                    } catch (e) { }
                }
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

export default function TemplateEditorPage() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <TemplateEditorContent />
        </Suspense>
    );
}
