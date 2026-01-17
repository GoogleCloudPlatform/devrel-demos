"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { PageHeader } from "@/components/ui/page-header";
import ScenarioForm from "@/components/ScenarioForm";

export default function NewScenarioPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    const handleCreate = async (formData: FormData) => {
        setLoading(true);
        try {
            const res = await fetch('/api/scenarios', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                toast.success("Scenario initialized successfully");
                router.push('/scenarios');
            } else {
                toast.error("Failed to create scenario");
            }
        } catch (e) {
            toast.error("Error creating scenario");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Create Scenario"
                description="Define a new standardized task for agent evaluation."
                backHref="/scenarios"
            />

            <ScenarioForm
                mode="create"
                onSubmit={handleCreate}
                isLoading={loading}
            />
        </div>
    );
}