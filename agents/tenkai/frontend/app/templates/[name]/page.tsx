'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import TemplateForm from "@/components/TemplateForm";
import { PageHeader } from "@/components/ui/page-header";

export default function TemplateEditorPage({ params }: { params: Promise<{ name: string }> }) {
    const router = useRouter();
    const [scenarios, setScenarios] = useState<any[]>([]);
    const [initialData, setInitialData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadData = async () => {
            const { name } = await params;
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
                    config: template.config || {} // Note: config might need parsing if content is raw
                });
                
                // If config is not in response, try to parse it from content
                if (!template.config && template.content) {
                    try {
                        const yaml = require('js-yaml');
                        setInitialData((prev: any) => ({
                            ...prev,
                            config: yaml.load(template.content)
                        }));
                    } catch (e) {}
                }
            } catch (e) {
                console.error(e);
                alert("Failed to load template editor");
            } finally {
                setLoading(false);
            }
        };
        loadData();
    }, [params]);

    if (loading) return <div className="p-20 text-center animate-pulse text-body">Loading Environment...</div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader 
                title="Edit Template" 
                description={`ID: ${initialData.id}`}
                backHref="/templates"
            />

            <TemplateForm scenarios={scenarios} initialData={initialData} mode="edit" />
        </div>
    );
}
