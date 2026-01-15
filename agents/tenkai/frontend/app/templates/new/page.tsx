"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TextArea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";

export default function NewTemplatePage() {
    const router = useRouter();
    const [submitting, setSubmitting] = useState(false);

    // Form state
    const [id, setId] = useState("");
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    // Simplistic config editor as textarea for now
    const [config, setConfig] = useState("alternatives:\n  - name: default\n    model: gemini-2.5-flash");

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSubmitting(true);
        try {
            const res = await fetch('/api/templates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ id, name, description, config_content: config })
            });
            if (res.ok) {
                toast.success("Template created");
                router.push('/templates');
            } else {
                const err = await res.text();
                toast.error("Failed to create template: " + err);
            }
        } catch (e) {
            toast.error("Error creating template");
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="p-8 max-w-3xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="New Template"
                description="Create a new experiment configuration template."
            />
            <Card className="p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-sm font-medium">ID (Slug)</label>
                            <Input
                                value={id}
                                onChange={e => setId(e.target.value)}
                                placeholder="e.g. basic-benchmark"
                                required
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-sm font-medium">Name</label>
                            <Input
                                value={name}
                                onChange={e => setName(e.target.value)}
                                placeholder="e.g. Basic Benchmark"
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Description</label>
                        <TextArea
                            value={description}
                            onChange={e => setDescription(e.target.value)}
                            placeholder="Description of this template"
                            rows={3}
                        />
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Configuration (YAML)</label>
                        <TextArea
                            value={config}
                            onChange={e => setConfig(e.target.value)}
                            placeholder="config.yaml content..."
                            rows={15}
                            className="font-mono text-xs"
                            required
                        />
                    </div>

                    <div className="pt-4 flex justify-end gap-2">
                        <Button type="button" variant="outline" onClick={() => router.back()}>Cancel</Button>
                        <Button type="submit" disabled={submitting}>
                            {submitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                            Create Template
                        </Button>
                    </div>
                </form>
            </Card>
        </div>
    );
}