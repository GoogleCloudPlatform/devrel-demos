"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getScenarios, getTemplates, Scenario, Template } from "../../api/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function NewExperimentPage() {
    const router = useRouter();
    const [scenarios, setScenarios] = useState<Scenario[]>([]);
    const [templates, setTemplates] = useState<Template[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);

    // Form state
    const [name, setName] = useState("");
    const [templateId, setTemplateId] = useState("");
    const [scenarioId, setScenarioId] = useState("");

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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const res = await fetch('/api/experiments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, template_id: templateId, scenario_id: scenarioId })
            });
            if (res.ok) {
                toast.success("Experiment created");
                router.push('/experiments');
            } else {
                toast.error("Failed to create experiment");
            }
        } catch (e) {
            toast.error("Error creating experiment");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) return <div className="flex justify-center p-12"><Loader2 className="w-8 h-8 animate-spin" /></div>;

    return (
        <div className="p-8 max-w-2xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="New Experiment"
                description="Launch a new agent evaluation run."
            />
            <Card className="p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Experiment Name</label>
                        <Input
                            value={name}
                            onChange={e => setName(e.target.value)}
                            placeholder="e.g. Gemini 2.0 Flash vs Pro"
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <Select
                            label="Template"
                            options={templates.map(t => ({ value: t.id, label: t.name }))}
                            value={templateId}
                            onChange={e => setTemplateId(e.target.value)}
                            required
                        />
                    </div>

                    <div className="space-y-2">
                        <Select
                            label="Scenario (Optional override)"
                            options={[{ value: "", label: "Defined in Template" }, ...scenarios.map(s => ({ value: s.id, label: s.name }))]}
                            value={scenarioId}
                            onChange={e => setScenarioId(e.target.value)}
                        />
                    </div>

                    <div className="pt-4 flex justify-end gap-2">
                        <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
                        <Button type="submit" disabled={submitting}>
                            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            Create Experiment
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}