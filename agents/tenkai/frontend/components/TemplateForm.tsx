'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input, TextArea } from "./ui/input";
import { Select } from "./ui/select";
import { ScenarioSelector } from "./ScenarioSelector";

import yaml from "js-yaml";

interface Scenario {
    id: string;
    name: string;
    description: string;
}

interface TemplateFormProps {
    scenarios: Scenario[];
    initialData?: any;
    mode?: 'create' | 'edit';
}

export default function TemplateForm({ scenarios, initialData, mode = 'create' }: TemplateFormProps) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // State for Visual Editor
    const [name, setName] = useState(initialData?.name || initialData?.config?.name || "");
    const [description, setDescription] = useState(initialData?.description || initialData?.config?.description || "");
    const [reps, setReps] = useState(initialData?.config?.reps || 1);
    const [concurrent, setConcurrent] = useState(initialData?.config?.concurrent || 1);
    const [timeout, setTimeoutVal] = useState(initialData?.config?.timeout || "");
    const [selectedScenarios, setSelectedScenarios] = useState<string[]>(
        Array.from(new Set(initialData?.config?.scenarios?.map((s: string | any) => {
            // Handle both legacy object {id: ...} and new string "scenarios/id"
            if (typeof s === 'string') return s.split('/').pop() || s;
            return String(s.id);
        }) || []))
    );
    const [alternatives, setAlternatives] = useState<any[]>(
        initialData?.config?.alternatives || [
            { name: "", description: "", system_prompt: "", settings: {} }
        ]
    );
    const [experimentControl, setExperimentControl] = useState(initialData?.config?.experiment_control || "");
    const [fileUploads, setFileUploads] = useState<Record<string, string>>({});

    const handleScenarioToggle = (id: string | number) => {
        const strId = String(id);
        setSelectedScenarios(prev => {
            const normalizedPrev = prev.map(String);
            if (normalizedPrev.includes(strId)) {
                return normalizedPrev.filter(s => s !== strId);
            }
            return [...normalizedPrev, strId];
        });
    };

    const addAlternative = () => {
        if (alternatives.length >= 10) return;
        setAlternatives([...alternatives, { name: "", description: "", system_prompt: "", command: "gemini", args: ["-y"], settings: {} }]);
    };

    const updateAlternative = (index: number, field: string, value: any) => {
        const newAlts = [...alternatives];
        newAlts[index] = { ...newAlts[index], [field]: value };
        setAlternatives(newAlts);
    };

    const handleFileRead = (file: File, callback: (content: string) => void) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            if (e.target?.result) callback(e.target.result as string);
        };
        reader.readAsText(file);
    };

    const handleAltFileUpload = (index: number, type: 'system_prompt' | 'context' | 'settings', file: File) => {
        handleFileRead(file, (content) => {
            const filename = file.name;
            setFileUploads(prev => ({ ...prev, [filename]: content }));
            
            // Update alternative config to reference the file path
            if (type === 'system_prompt') {
                updateAlternative(index, 'system_prompt_file', `./${filename}`);
                updateAlternative(index, 'system_prompt', ''); // Clear inline
            } else if (type === 'context') {
                updateAlternative(index, 'context_file_path', `./${filename}`);
                updateAlternative(index, 'context', ''); // Clear inline
            } else if (type === 'settings') {
                updateAlternative(index, 'settings_path', `./${filename}`);
                updateAlternative(index, 'settings', {}); // Clear inline
            }
        });
    };

    const removeAlternative = (index: number) => {
        setAlternatives(alternatives.filter((_, i) => i !== index));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        if (selectedScenarios.length === 0) {
            setError("At least one scenario must be selected.");
            setLoading(false);
            return;
        }

        const finalConfig = {
            reps,
            concurrent,
            timeout,
            experiment_control: experimentControl,
            scenarios: selectedScenarios.map(id => `scenarios/${id}`),
            alternatives: alternatives.map(a => ({
                name: a.name,
                description: a.description,
                system_prompt: a.system_prompt,
                system_prompt_file: a.system_prompt_file,
                context: a.context,
                context_file_path: a.context_file_path,
                settings_path: a.settings_path,
                command: a.command || "gemini",
                args: (Array.isArray(a.args) && a.args.length > 0) ? a.args : (typeof a.args === 'string' && a.args.trim().length > 0 ? a.args.split(' ').filter(Boolean) : ["-y"]),
                settings: typeof a.settings === 'string' ? JSON.parse(a.settings) : a.settings
            }))
        };

        const finalYaml = yaml.dump({
            name,
            description,
            ...finalConfig
        });

        const payload = {
            name,
            description,
            config: finalConfig,
            yaml_content: finalYaml,
            files: fileUploads
        };

        const url = mode === 'create' ? '/api/templates' : `/api/templates/${initialData.id}/config`;
        const method = mode === 'create' ? 'POST' : 'PUT';

        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                if (mode === 'create') {
                    router.push('/templates');
                } else {
                    router.refresh();
                    alert("Template updated successfully");
                }
            } else {
                const data = await res.json();
                setError(data.error || "Failed to save template");
            }
        } catch (e) {
            setError("Connection error. Is the runner active?");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-8 text-body max-w-6xl mx-auto">
            {/* Header / Actions */}
            <div className="flex justify-end items-center bg-[#09090b] border border-[#27272a] p-2 rounded-md">
                <div className="flex items-center gap-4 px-2">
                    {error && <span className="text-red-500 font-bold uppercase tracking-tighter">{error}</span>}
                    <Button type="submit" variant="default" size="lg" isLoading={loading}>
                        Save Template
                    </Button>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
                <div className="md:col-span-4 space-y-8">
                    <Card title="General">
                        <div className="space-y-6">
                            <Input label="Template Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="experiment-name" />
                            <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={4} placeholder="Experiment description..." />
                        </div>
                    </Card>

                    <Card title="Execution">
                        <div className="space-y-4">
                            <Input label="Repetitions" type="number" value={reps} onChange={(e) => setReps(Number(e.target.value))} />
                            <Input label="Max Concurrent" type="number" value={concurrent} onChange={(e) => setConcurrent(Number(e.target.value))} />
                            <Input label="Exec Timeout" value={timeout} onChange={(e) => setTimeoutVal(e.target.value)} placeholder="10m" />
                            <Select
                                label="Control"
                                value={experimentControl}
                                onChange={(e) => setExperimentControl(e.target.value)}
                                options={Array.from(new Set(alternatives.map(a => a.name).filter(n => n && n.trim() !== ""))).map(name => ({ label: name, value: name }))}
                            />
                        </div>
                    </Card>
                </div>

                <div className="md:col-span-8 space-y-8">
                    <ScenarioSelector
                        scenarios={scenarios}
                        selectedIds={selectedScenarios}
                        onToggle={handleScenarioToggle}
                    />

                    <Card>
                        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                            <CardTitle>Alternatives</CardTitle>
                            <Button type="button" variant="ghost" size="sm" onClick={addAlternative} className="text-primary font-bold uppercase hover:text-foreground transition-colors">+ Add Alt</Button>
                        </CardHeader>
                        <CardContent className="space-y-6 pt-6">
                            {alternatives.map((alt, idx) => {
                                const colorClass = [
                                    "border-indigo-500/30 bg-indigo-500/5",
                                    "border-emerald-500/30 bg-emerald-500/5",
                                    "border-amber-500/30 bg-amber-500/5",
                                    "border-rose-500/30 bg-rose-500/5",
                                    "border-cyan-500/30 bg-cyan-500/5",
                                    "border-violet-500/30 bg-violet-500/5",
                                    "border-orange-500/30 bg-orange-500/5",
                                    "border-lime-500/30 bg-lime-500/5",
                                    "border-fuchsia-500/30 bg-fuchsia-500/5",
                                    "border-sky-500/30 bg-sky-500/5",
                                ][idx % 10];

                                return (
                                <div key={idx}>
                                    {idx > 0 && (
                                        <div className="py-6 flex items-center gap-4 text-zinc-700">
                                            <div className="h-px bg-border flex-1 border-t border-dashed" />
                                            <span className="text-xs font-mono uppercase font-bold tracking-widest">Alternative {idx + 1}</span>
                                            <div className="h-px bg-border flex-1 border-t border-dashed" />
                                        </div>
                                    )}
                                    <div className={`panel p-5 relative border rounded-xl hover:border-zinc-700 transition-colors ${colorClass}`}>
                                        <div className="absolute -left-3 -top-3 w-6 h-6 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center font-bold text-xs text-zinc-400 font-mono shadow-sm">
                                            {idx + 1}
                                        </div>
                                        <button
                                            type="button"
                                            onClick={() => removeAlternative(idx)}
                                            className="absolute top-4 right-4 text-zinc-500 hover:text-red-400 transition-colors p-1 hover:bg-white/5 rounded"
                                            title="Remove Alternative"
                                        >
                                            ✕
                                        </button>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-2">
                                            <Input label="Identifier" value={alt.name} onChange={(e) => updateAlternative(idx, 'name', e.target.value)} placeholder="e.g. gemini-1.5-flash" />
                                            <Input label="Short Desc" value={alt.description} onChange={(e) => updateAlternative(idx, 'description', e.target.value)} placeholder="Brief description..." />

                                            <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-6">
                                                <Input label="Command" placeholder="gemini" value={alt.command || ""} onChange={(e) => updateAlternative(idx, 'command', e.target.value)} />
                                                <Input label="Arguments" placeholder="-y" value={Array.isArray(alt.args) ? alt.args.join(" ") : (alt.args || "")} onChange={(e) => updateAlternative(idx, 'args', e.target.value.split(" "))} />
                                            </div>

                                            <div className="md:col-span-2">
                                                <div className="flex justify-between items-center mb-1">
                                                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">System Prompt Override</label>
                                                    <div className="relative">
                                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files && handleAltFileUpload(idx, 'system_prompt', e.target.files[0])} />
                                                        <span className="text-[10px] uppercase font-bold text-indigo-400 cursor-pointer hover:underline">Upload File</span>
                                                    </div>
                                                </div>
                                                {alt.system_prompt_file && <div className="text-xs font-mono text-emerald-400 mb-1">File: {alt.system_prompt_file}</div>}
                                                <TextArea value={alt.system_prompt} onChange={(e) => updateAlternative(idx, 'system_prompt', e.target.value)} rows={3} className="font-mono text-sm" placeholder="Inline system prompt..." />
                                            </div>

                                            <div className="md:col-span-2">
                                                <div className="flex justify-between items-center mb-1">
                                                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">GEMINI.md Content (Context)</label>
                                                    <div className="relative">
                                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files && handleAltFileUpload(idx, 'context', e.target.files[0])} />
                                                        <span className="text-[10px] uppercase font-bold text-indigo-400 cursor-pointer hover:underline">Upload File</span>
                                                    </div>
                                                </div>
                                                {alt.context_file_path && <div className="text-xs font-mono text-emerald-400 mb-1">File: {alt.context_file_path}</div>}
                                                <TextArea value={alt.context || ""} onChange={(e) => updateAlternative(idx, 'context', e.target.value)} rows={3} className="font-mono text-sm" placeholder="# Context Information..." />
                                            </div>

                                            <div className="md:col-span-2">
                                                <div className="flex justify-between items-center mb-1">
                                                    <label className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Settings JSON Override</label>
                                                    <div className="relative">
                                                        <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={(e) => e.target.files && handleAltFileUpload(idx, 'settings', e.target.files[0])} />
                                                        <span className="text-[10px] uppercase font-bold text-indigo-400 cursor-pointer hover:underline">Upload File</span>
                                                    </div>
                                                </div>
                                                {alt.settings_path && <div className="text-xs font-mono text-emerald-400 mb-1">File: {alt.settings_path}</div>}
                                                <TextArea value={typeof alt.settings === 'string' ? alt.settings : JSON.stringify(alt.settings, null, 2)} onChange={(e) => updateAlternative(idx, 'settings', e.target.value)} rows={3} className="font-mono text-sm" placeholder="{}" />
                                            </div>
                                        </div>
                                    </div>
                                </div>
                                );
                            })}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </form>
    );
}