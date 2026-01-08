'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from 'next/link';
import { Button } from "./ui/button";
import { Input, TextArea, Select } from "./ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "./ui/card";
import { Badge } from "./ui/badge";
import { cn } from "@/utils/cn";
import { ScenarioSelector } from "./ScenarioSelector";

export default function ExperimentForm({ templates, scenarios }: { templates: any[], scenarios: any[] }) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [selectedTemplate, setSelectedTemplate] = useState<string>("");
    const [templateDetails, setTemplateDetails] = useState<any>(null);

    // Form states
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [reps, setReps] = useState(1);
    const [concurrent, setConcurrent] = useState(1);
    const [selectedScenarios, setSelectedScenarios] = useState<string[]>([]);
    const [selectedAlternatives, setSelectedAlternatives] = useState<string[]>([]);
    const [controlAlt, setControlAlt] = useState<string>("");
    const [timeout, setTimeout] = useState("10m");

    useEffect(() => {
        if (templates.length > 0 && !selectedTemplate) {
            setSelectedTemplate(templates[0].id);
        }
    }, [templates]);

    useEffect(() => {
        if (!selectedTemplate) return;

        const fetchTemplate = async () => {
            const res = await fetch(`/api/templates/${selectedTemplate}/config`);
            const data = await res.json();
            setTemplateDetails(data);

            // Auto-populate based on template
            setName(`${data.name}_run`);
            setDescription(data.description || "");
            setReps(data.config.reps || 1);
            setConcurrent(data.config.concurrent || 1);
            setSelectedScenarios(data.config.scenarios.map((s: any) => {
                if (typeof s === 'string') {
                    const parts = s.split('/');
                    return parts[parts.length - 1];
                }
                return String(s.id);
            }));
            setSelectedAlternatives(data.config.alternatives.map((a: any) => a.name));
            setControlAlt(data.config.experiment_control || "");
            setTimeout(data.config.timeout || "10m");
        };
        fetchTemplate();
    }, [selectedTemplate]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);

        const payload = {
            name,
            description,
            template_id: selectedTemplate,
            reps: Number(reps),
            concurrent: Number(concurrent),
            scenarios: selectedScenarios,
            alternatives: selectedAlternatives,
            control: controlAlt,
            timeout: timeout
        };

        try {
            const res = await fetch('/api/experiments/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                router.refresh();
                router.push('/experiments');
            } else {

                alert("Failed to launch experiment");
            }
        } catch (e) {
            alert("Error launching experiment");
        } finally {
            setLoading(false);
        }
    };

    const totalJobs = selectedScenarios.length * selectedAlternatives.length * reps;

    const parseDurationMinutes = (d: string): number => {
        if (!d) return 10;
        const match = d.match(/(\d+)([hms])/);
        if (!match) {
            const val = parseInt(d);
            return isNaN(val) ? 10 : val;
        }
        const val = parseInt(match[1]);
        const unit = match[2];
        if (unit === 'h') return val * 60;
        if (unit === 'm') return val;
        if (unit === 's') return Math.ceil(val / 60) || 1;
        return 10;
    };

    const timeoutMins = parseDurationMinutes(timeout);
    const estimatedTime = Math.ceil((totalJobs / Math.max(1, concurrent)) * timeoutMins);

    return (
        <form onSubmit={handleSubmit} className="space-y-8 max-w-5xl">
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                {/* Left Column: Core Config */}
                <div className="md:col-span-8 space-y-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>Primary Identity</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <Select
                                label="Base Template"
                                value={selectedTemplate}
                                onChange={(e) => setSelectedTemplate(e.target.value)}
                                options={templates.map(t => ({ value: t.id, label: t.name }))}
                            />
                            <Input label="Experiment Name" value={name} onChange={(e) => setName(e.target.value)} required />
                            <TextArea label="Context / Objectives" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Alternative Selection</CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="grid grid-cols-1 gap-4">
                                {templateDetails?.config.alternatives.map((alt: any) => {
                                    const isSelected = selectedAlternatives.includes(alt.name);
                                    return (
                                        <button
                                            key={alt.name}
                                            type="button"
                                            onClick={() => {
                                                if (isSelected) setSelectedAlternatives(prev => prev.filter(a => a !== alt.name));
                                                else setSelectedAlternatives(prev => [...prev, alt.name]);
                                            }}
                                            className={cn(
                                                "text-left p-4 rounded-lg border transition-all flex justify-between items-center group bg-card",
                                                isSelected
                                                    ? "border-primary bg-primary/5 shadow-[0_0_0_1px] shadow-primary"
                                                    : "border-border hover:border-primary/50"
                                            )}
                                        >
                                            <div className="flex-1">
                                                <div className="flex items-center gap-3 mb-1">
                                                    <h4 className={cn("font-bold transition-colors", isSelected ? 'text-primary' : 'text-foreground')}>{alt.name}</h4>
                                                    {alt.name === controlAlt && <Badge variant="secondary">Control</Badge>}
                                                </div>
                                                <p className="text-muted-foreground text-sm line-clamp-1">{alt.description || "Experimental variation"}</p>
                                            </div>
                                            <div className={cn(
                                                "w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all",
                                                isSelected ? "bg-primary border-primary text-primary-foreground" : "border-muted-foreground"
                                            )}>
                                                {isSelected && <span className="text-[10px] font-black">✓</span>}
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </CardContent>
                    </Card>

                    <ScenarioSelector
                        scenarios={templateDetails?.config.scenarios.map((scenCfg: any) => {
                            // Handle both string format "scenarios/ID" and object format {id: ID}
                            let id = "";
                            if (typeof scenCfg === 'string') {
                                const partes = scenCfg.split('/');
                                id = partes[partes.length - 1];
                            } else {
                                id = String(scenCfg.id);
                            }

                            const fullScen = scenarios.find(s => String(s.id) === id);
                            return {
                                id: id,
                                name: fullScen ? fullScen.name : `Scenario ${id}`,
                                description: fullScen ? fullScen.description : (typeof scenCfg === 'string' ? scenCfg : "")
                            };
                        }) || []}
                        selectedIds={selectedScenarios}
                        onToggle={(id) => {
                            if (selectedScenarios.includes(id)) {
                                setSelectedScenarios(prev => prev.filter(s => s !== id));
                            } else {
                                setSelectedScenarios(prev => [...prev, id]);
                            }
                        }}
                    />
                </div>

                {/* Right Column: Execution Parameters */}
                <div className="md:col-span-4 space-y-8">
                    <Card>
                        <CardHeader>
                            <CardTitle>Runtime Params</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <Input label="Repetitions" type="number" value={reps} onChange={(e) => setReps(Number(e.target.value))} />
                            <Input label="Max Concurrency" type="number" value={concurrent} onChange={(e) => setConcurrent(Number(e.target.value))} />
                            <Input label="Timeout (e.g. 5m, 1h)" value={timeout} onChange={(e) => setTimeout(e.target.value)} />

                            <div className="pt-4 border-t space-y-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-muted-foreground font-bold text-xs uppercase tracking-tighter">Total Jobs</span>
                                    <span className="text-xl font-black text-primary">{totalJobs}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-muted-foreground font-bold text-xs uppercase tracking-tighter">Estimated Duration</span>
                                    <span className="font-mono text-foreground">~{estimatedTime}m</span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>

                    <div className="space-y-4">
                        <Button type="submit" variant="default" size="lg" className="w-full" isLoading={loading}>
                            Launch
                        </Button>
                        <Link href="/experiments" className="block w-full">
                            <Button variant="ghost" className="w-full">
                                Cancel
                            </Button>
                        </Link>
                    </div>
                </div>
            </div>
        </form>
    );
}