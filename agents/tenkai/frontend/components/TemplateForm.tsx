'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Input, TextArea } from "./ui/input";
import { ConfigBlock, ConfigBlockType } from "@/types/domain";
import yaml from "js-yaml";
import { Plus } from "lucide-react";
import AlternativeCard from "./AlternativeCard";

interface TemplateFormProps {
    blocks: ConfigBlock[];
    initialData?: any;
    mode?: 'create' | 'edit';
    isLocked?: boolean;
}

export default function TemplateForm({ blocks, initialData, mode = 'create', isLocked = false }: TemplateFormProps) {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Filtered blocks helper
    const getBlocksByType = (type: ConfigBlockType) => blocks.filter(b => b.type === type);

    // State for Visual Editor
    const [name, setName] = useState(initialData?.name || initialData?.config?.name || "");
    const [description, setDescription] = useState(initialData?.description || initialData?.config?.description || "");
    // Runtime Config removed from Template Editor (defaults used)
    // const [reps, setReps] = useState(initialData?.config?.reps || 1);
    // const [concurrent, setConcurrent] = useState(initialData?.config?.concurrent || 1);
    // const [timeout, setTimeoutVal] = useState(initialData?.config?.timeout || "");


    // Robust ID generator
    const safeUUID = () => {
        if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
        return `id-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    };

    // Alternatives State
    // We add a temporary _ui_id to track items stably in the UI even if names change or are dupes
    const [alternatives, setAlternatives] = useState<any[]>(
        (initialData?.config?.alternatives || [
            { name: "default", description: "", command: "", args: [], settings: {} }
        ]).map((a: any) => ({ ...a, _ui_id: safeUUID() }))
    );

    // Effect: Auto-populate first agent for default/existing alternatives if command is empty
    // Only runs once on mount if blocks are available
    useState(() => {
        if (blocks.length > 0) {
            const firstAgent = blocks.find(b => b.type === 'agent');
            if (firstAgent) {
                try {
                    const c = JSON.parse(firstAgent.content);
                    setAlternatives(prev => prev.map(a => {
                        if (!a.command) {
                            return { ...a, command: c.command, args: c.args };
                        }
                        return a;
                    }));
                } catch (e) { }
            }
        }
    });
    const [experimentControl, setExperimentControl] = useState(initialData?.config?.experiment_control || "");

    const addAlternative = () => {
        if (alternatives.length >= 10) return;

        // Auto-populate with first agent
        let defaultAgent = { command: "", args: [] as string[] };
        const firstAgentBlock = blocks.find(b => b.type === 'agent');
        if (firstAgentBlock) {
            try {
                const c = JSON.parse(firstAgentBlock.content);
                defaultAgent.command = c.command;
                defaultAgent.args = c.args;
            } catch (e) {
                console.error("Failed to parse default agent block", e);
            }
        }

        setAlternatives([...alternatives, {
            _ui_id: safeUUID(),
            name: `alt-${alternatives.length + 1}`,
            description: "",
            command: defaultAgent.command,
            args: defaultAgent.args,
            // Initialize optional lists
            extensions: [],
            skills: [],
            mcp_servers: [],
            settings_blocks: []
        }]);
    };

    const updateAlternative = (index: number, field: string, value: any) => {
        const newAlts = [...alternatives];
        newAlts[index] = { ...newAlts[index], [field]: value };
        setAlternatives(newAlts);
    };

    const removeAlternative = (index: number) => {
        if (alternatives.length <= 1) return; // Prevent deleting last one
        setAlternatives(alternatives.filter((_, i) => i !== index));
    };

    const duplicateAlternative = (index: number) => {
        if (alternatives.length >= 10) return;
        const altToCopy = alternatives[index];
        const newAlt = {
            ...altToCopy,
            _ui_id: safeUUID(),
            name: `${altToCopy.name}-copy`,
            description: `Copy of ${altToCopy.description}`
        };
        const newAlts = [...alternatives];
        newAlts.splice(index + 1, 0, newAlt);
        setAlternatives(newAlts);
    };

    // Helper to get selected block ID/Name for dropdowns
    const getSelectedBlockName = (type: ConfigBlockType, content: any) => {
        if (!content) return "(none selected)";
        // Content might be a string (system prompt) or object (agent).
        const contentStr = typeof content === 'string' ? content : JSON.stringify(content);

        const match = blocks.find(b => {
            if (b.type !== type) return false;
            // Compare parsed if JSON, raw if text
            if (type === 'system_prompt' || type === 'context') {
                return b.content.trim() === contentStr.trim();
            }
            try {
                const bContent = JSON.parse(b.content);
                const cContent = typeof content === 'string' ? JSON.parse(content) : content;
                return JSON.stringify(bContent) === JSON.stringify(cContent);
            } catch {
                return b.content === contentStr;
            }
        });
        return match ? match.name : (content ? "Custom/Manual" : "(none selected)");
    };

    // For Agent specifically, we check command/args match
    const getAgentBlockName = (alt: any) => {
        if (!alt.command) return "(Select Agent)";
        const match = blocks.find(b => {
            if (b.type !== 'agent') return false;
            try {
                const c = JSON.parse(b.content);
                // Compare command and args
                // args might be string or array
                const bArgs = Array.isArray(c.args) ? c.args.join(" ") : (c.args || "");
                const altArgs = Array.isArray(alt.args) ? alt.args.join(" ") : (alt.args || "");
                return c.command === alt.command && bArgs === altArgs;
            } catch { return false; }
        });
        return match ? match.name : `${alt.command} (Custom)`;
    };


    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        // Validate: Every alternative must have a command (Agent)
        const invalidAlt = alternatives.find(a => !a.command);
        if (invalidAlt) {
            setError(`Alternative "${invalidAlt.name}" is missing an Agent.`);
            setLoading(false);
            return;
        }

        const finalConfig = {
            reps: 1, // Default (overridden at runtime)
            concurrent: 1, // Default (overridden at runtime)
            timeout: "30m", // Default
            experiment_control: experimentControl,
            scenarios: [], // Decoupled: Scenarios selected at runtime
            alternatives: alternatives.map(a => ({
                name: a.name,
                description: a.description,

                // Agent
                command: a.command,
                args: Array.isArray(a.args) ? a.args : (typeof a.args === 'string' ? a.args.split(" ") : []),

                // Optional Single Blocks
                system_prompt: a.system_prompt,
                context: a.context,

                // Optional Lists
                settings_blocks: a.settings_blocks || [],
                extensions: a.extensions || [],
                skills: a.skills || [],
                mcp_servers: a.mcp_servers || [],

                // Clean up legacy fields just in case
                system_prompt_file: undefined,
                context_file_path: undefined,
                settings_path: undefined,
                settings: {} // Empty inline settings, use blocks
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
            files: {}
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
                    toast.success("Template created successfully");
                    router.push('/templates');
                } else {
                    router.refresh();
                    toast.success("Template updated successfully");
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
        <form onSubmit={handleSubmit} className="space-y-6 max-w-6xl mx-auto pb-20">
            {/* Top Bar - Buttons Only */}
            <div className="flex justify-end items-center pb-4 border-b border-border">
                <div className="flex gap-4 items-center">
                    {error && <span className="text-red-500 font-bold text-sm tracking-tight bg-red-500/10 px-2 py-1 rounded">{error}</span>}
                    <Button type="submit" variant="default" isLoading={loading} disabled={isLocked}>
                        Save Template
                    </Button>
                    <Button type="button" variant="ghost" onClick={() => router.back()}>
                        Close
                    </Button>
                </div>
            </div>

            {/* General & Runtime Config Grid */}
            <div className="md:col-span-3 border border-border rounded-xl p-6 bg-card space-y-4">
                <h3 className="font-semibold text-sm uppercase tracking-wider text-muted-foreground mb-4">General Info</h3>
                <div className="grid gap-4">
                    <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="My Experiment" className="font-bold text-lg" />
                    <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="(Optional) Describe the purpose of this experiment..." />
                </div>
            </div>

            {/* Alternatives Section */}
            <div className="border border-border rounded-xl p-6 bg-muted/5">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold">Alternatives</h3>
                </div>

                <div className="space-y-6">
                    {alternatives.map((alt, idx) => (
                        <AlternativeCard
                            key={alt._ui_id || idx}
                            alt={alt}
                            index={idx}
                            blocks={blocks}
                            isControl={experimentControl === alt.name}
                            onUpdate={(field: string, val: any) => updateAlternative(idx, field, val)}
                            onSetControl={() => setExperimentControl(experimentControl === alt.name ? "" : alt.name)}
                            onDelete={() => removeAlternative(idx)}
                            onDuplicate={() => duplicateAlternative(idx)}
                            getAgentName={() => getAgentBlockName(alt)}
                            getBlockName={(t, c) => getSelectedBlockName(t, c)}
                            isLocked={isLocked}
                        />
                    ))}

                    <Button type="button" variant="outline" onClick={addAlternative} disabled={isLocked} className="w-full py-8 border-dashed border-2 hover:border-primary hover:bg-primary/5 transition-all">
                        <Plus className="mr-2" /> Add Alternative
                    </Button>
                </div>
            </div>
        </form>
    );
}