"use client";

import { useState, useEffect } from "react";
import { getBlocks } from "@/lib/api";
import TemplateForm from "@/components/TemplateForm";
import { PageHeader } from "@/components/ui/page-header";
import { Loader2 } from "lucide-react";

export default function NewTemplatePage() {
    const [blocks, setBlocks] = useState<any[] | null>(null);

    useEffect(() => {
        getBlocks().then(setBlocks);
    }, []);

    if (!blocks) return <div className="p-20 flex justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="p-8 max-w-7xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Design Template"
                description="Configure a new benchmarking template."
                backHref="/templates"
                backLabel="Templates"
            />

            <TemplateForm blocks={blocks} />
        </div>
    );
}