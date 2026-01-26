'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Input, TextArea } from "./ui/input";
import { ConfigBlock, ConfigBlockType } from "@/types/domain";
import yaml from "js-yaml";
import { Trash2, Copy, Plus, X, Search, Check } from "lucide-react";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

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

// ------------------------------------------------------------------
// Sub-components (could receive their own files but kept here for now)
// ------------------------------------------------------------------

interface AlternativeCardProps {
    alt: any;
    index: number;
    blocks: ConfigBlock[];
    isControl: boolean;
    onUpdate: (field: string, value: any) => void;
    onSetControl: () => void;
    onDelete: () => void;
    onDuplicate: () => void;
    getAgentName: (alt: any) => string;
    getBlockName: (type: ConfigBlockType, content: any) => string;
    isLocked: boolean;
}

function AlternativeCard({
    alt, index, blocks, isControl, onUpdate, onSetControl, onDelete, onDuplicate,
    getAgentName, getBlockName, isLocked
}: AlternativeCardProps) {
    return (
        <div className="bg-card border border-border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow">
            {/* Header Row */}
            <div className="flex items-center gap-4 mb-4">
                <Input
                    value={alt.name}
                    onChange={(e) => onUpdate('name', e.target.value)}
                    className="font-bold flex-1"
                    placeholder="Alternative Name"
                    disabled={isLocked}
                />

                <div
                    className={cn(
                        "flex items-center gap-2 cursor-pointer px-3 py-2 rounded-md border transition-colors select-none",
                        isControl ? "bg-primary/10 border-primary text-primary" : "bg-muted hover:bg-muted/80 border-transparent text-muted-foreground"
                    )}
                    onClick={!isLocked ? onSetControl : undefined}
                >
                    <div className={cn("w-4 h-4 border rounded flex items-center justify-center", isControl ? "bg-primary border-primary" : "border-muted-foreground")}>
                        {isControl && <Check size={12} className="text-white" />}
                    </div>
                    <span className="text-sm font-bold uppercase tracking-wider">Control</span>
                </div>

                <div className="flex gap-1 ml-2">
                    <Button type="button" variant="ghost" size="icon" onClick={onDuplicate} disabled={isLocked} title="Duplicate">
                        <Copy size={16} className="text-muted-foreground" />
                    </Button>
                    <Button type="button" variant="ghost" size="icon" onClick={onDelete} disabled={isLocked} title="Delete">
                        <X size={16} className="text-muted-foreground hover:text-red-500" />
                    </Button>
                </div>
            </div>

            {/* Description Row */}
            <div className="mb-6">
                <Input
                    value={alt.description || ""}
                    onChange={(e) => onUpdate('description', e.target.value)}
                    placeholder="(Optional) Description"
                    className="text-muted-foreground text-sm"
                    disabled={isLocked}
                />
            </div>

            {/* Selectors Grid */}
            <div className="space-y-4 mb-6">
                {/* Agent (Required) */}
                <div className="grid grid-cols-12 gap-4 items-center">
                    <label className="col-span-3 font-medium text-sm text-muted-foreground">Agent</label>
                    <div className="col-span-9">
                        <BlockCombobox
                            type="agent"
                            blocks={blocks}
                            valueContent={null} // We rely on displayValue
                            displayValue={getAgentName(alt)}
                            onSelect={(b) => {
                                try {
                                    const c = JSON.parse(b.content);
                                    onUpdate('command', c.command);
                                    onUpdate('args', c.args);
                                } catch (e) { toast.error("Invalid Agent Block"); }
                            }}
                            required
                            disabled={isLocked}
                        />
                    </div>
                </div>

                {/* System Prompt (Optional) */}
                <div className="grid grid-cols-12 gap-4 items-center">
                    <label className="col-span-3 font-medium text-sm text-muted-foreground">System Prompt</label>
                    <div className="col-span-9">
                        <BlockCombobox
                            type="system_prompt"
                            blocks={blocks}
                            valueContent={alt.system_prompt}
                            displayValue={getBlockName('system_prompt', alt.system_prompt)}
                            onSelect={(b) => onUpdate('system_prompt', b.content)}
                            onClear={() => onUpdate('system_prompt', "")}
                            disabled={isLocked}
                        />
                    </div>
                </div>

                {/* Context (Optional) */}
                <div className="grid grid-cols-12 gap-4 items-center">
                    <label className="col-span-3 font-medium text-sm text-muted-foreground">Context File</label>
                    <div className="col-span-9">
                        <BlockCombobox
                            type="context"
                            blocks={blocks}
                            valueContent={alt.context}
                            displayValue={getBlockName('context', alt.context)}
                            onSelect={(b) => onUpdate('context', b.content)}
                            onClear={() => onUpdate('context', "")}
                            disabled={isLocked}
                        />
                    </div>
                </div>
            </div>

            {/* Options Tags */}
            <div className="grid grid-cols-12 gap-4 items-start">
                <label className="col-span-3 font-medium text-sm text-muted-foreground pt-2">Options</label>
                <div className="col-span-9 flex flex-wrap gap-2 items-center">
                    {/* Render existing options */}
                    {/* Skills */}
                    {(alt.skills || []).map((s: any, i: number) => (
                        <OptionChip key={`skill-${i}`} type="skill" name={s.name || s.name} onRemove={() => {
                            const n = [...alt.skills]; n.splice(i, 1); onUpdate('skills', n);
                        }} disabled={isLocked} />
                    ))}
                    {/* Extensions */}
                    {(alt.extensions || []).map((s: any, i: number) => (
                        <OptionChip key={`ext-${i}`} type="extension" name={s.name || s.name} onRemove={() => {
                            const n = [...alt.extensions]; n.splice(i, 1); onUpdate('extensions', n);
                        }} disabled={isLocked} />
                    ))}
                    {/* MCP */}
                    {(alt.mcp_servers || []).map((s: any, i: number) => (
                        <OptionChip key={`mcp-${i}`} type="mcp_server" name={s.name || s.name} onRemove={() => {
                            const n = [...alt.mcp_servers]; n.splice(i, 1); onUpdate('mcp_servers', n);
                        }} disabled={isLocked} />
                    ))}
                    {/* Settings */}
                    {(alt.settings_blocks || []).map((s: any, i: number) => (
                        <OptionChip key={`set-${i}`} type="settings" name={s.name || "Settings"} onRemove={() => {
                            const n = [...alt.settings_blocks]; n.splice(i, 1); onUpdate('settings_blocks', n);
                        }} disabled={isLocked} />
                    ))}

                    {/* Add Button */}
                    <AddOptionPopover blocks={blocks} onAdd={(type: ConfigBlockType, block: ConfigBlock) => {
                        try {
                            const content = JSON.parse(block.content);
                            // Use block.name as the configuration 'name' if not present, or overwrite it?
                            // User requested "it's just name", suggesting the block name should be the identifier.
                            const blockData = { ...content, name: block.name };
                            // Add based on type
                            if (type === 'skill') {
                                // Avoid dupes
                                if (!alt.skills?.find((x: any) => x.name === block.name)) {
                                    onUpdate('skills', [...(alt.skills || []), blockData]);
                                }
                            } else if (type === 'extension') {
                                if (!alt.extensions?.find((x: any) => x.name === block.name)) {
                                    onUpdate('extensions', [...(alt.extensions || []), blockData]);
                                }
                            } else if (type === 'mcp_server') {
                                if (!alt.mcp_servers?.find((x: any) => x.name === block.name)) {
                                    onUpdate('mcp_servers', [...(alt.mcp_servers || []), blockData]);
                                }
                            } else if (type === 'settings') {
                                // Settings can be dupliated? Maybe. But let's allow it.
                                onUpdate('settings_blocks', [...(alt.settings_blocks || []), blockData]);
                            }
                        } catch (e) { toast.error("Invalid block content"); }
                    }} disabled={isLocked} />
                </div>
            </div>

        </div>
    );
}

interface OptionChipProps {
    type: 'skill' | 'extension' | 'mcp_server' | 'settings';
    name: string;
    onRemove: () => void;
    disabled: boolean;
}

function OptionChip({ type, name, onRemove, disabled }: OptionChipProps) {
    const styles: any = {
        skill: "bg-sky-500/10 text-sky-600 border-sky-200",
        extension: "bg-indigo-500/10 text-indigo-600 border-indigo-200",
        mcp_server: "bg-orange-500/10 text-orange-600 border-orange-200",
        settings: "bg-slate-500/10 text-slate-600 border-slate-200"
    }
    const labels: any = {
        skill: "Skill", extension: "Extension", mcp_server: "MCP", settings: "Settings"
    }

    return (
        <Badge variant="outline" className={cn("pl-2 pr-1 py-1 flex items-center gap-1 font-normal", styles[type])}>
            {name}
            <span className="font-bold opacity-70 ml-1 text-[10px] uppercase tracking-wider">[{labels[type]}]</span>
            {!disabled && (
                <button type="button" onClick={onRemove} className="ml-1 hover:bg-black/10 rounded-full p-0.5 transition-colors">
                    <X size={12} />
                </button>
            )}
        </Badge>
    )
}

interface BlockComboboxProps {
    type: ConfigBlockType;
    blocks: ConfigBlock[];
    valueContent: any;
    displayValue: string;
    onSelect: (block: ConfigBlock) => void;
    onClear?: () => void;
    required?: boolean;
    disabled: boolean;
}

function BlockCombobox({ type, blocks, valueContent, displayValue, onSelect, onClear, required, disabled }: BlockComboboxProps) {
    const [open, setOpen] = useState(false)
    const filtered = blocks.filter((b: ConfigBlock) => b.type === type);

    return (
        <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
                <Button
                    type="button"
                    variant="outline"
                    role="combobox"
                    aria-expanded={open}
                    className="w-full justify-between font-normal"
                    disabled={disabled}
                >
                    <span className={cn(!valueContent && !required ? "text-muted-foreground italic" : "")}>
                        {displayValue}
                    </span>
                    <Search className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0" align="start">
                <Command>
                    <CommandInput placeholder={`Search ${type}...`} />
                    <CommandList>
                        <CommandEmpty>No blocks found.</CommandEmpty>
                        <CommandGroup>
                            {!required && (
                                <CommandItem onSelect={() => { onClear?.(); setOpen(false); }}>
                                    <span className="italic text-muted-foreground">(none selected)</span>
                                </CommandItem>
                            )}
                            {filtered.map((block: any) => (
                                <CommandItem
                                    key={block.id}
                                    value={block.name}
                                    onSelect={() => {
                                        onSelect(block)
                                        setOpen(false)
                                    }}
                                >
                                    <Check
                                        className={cn(
                                            "mr-2 h-4 w-4",
                                            displayValue === block.name ? "opacity-100" : "opacity-0"
                                        )}
                                    />
                                    {block.name}
                                </CommandItem>
                            ))}
                        </CommandGroup>
                    </CommandList>
                </Command>
            </PopoverContent>
        </Popover>
    )
}

interface AddOptionPopoverProps {
    blocks: ConfigBlock[];
    onAdd: (type: ConfigBlockType, block: ConfigBlock) => void;
    disabled: boolean;
}

function AddOptionPopover({ blocks, onAdd, disabled }: AddOptionPopoverProps) {
    const [open, setOpen] = useState(false);
    const [step, setStep] = useState<'type' | 'block'>('type');
    const [selectedType, setSelectedType] = useState<ConfigBlockType | null>(null);

    const typeOptions = [
        { type: "skill", label: "Skills", desc: "Agent capabilities" },
        { type: "extension", label: "Extensions", desc: "Workspace tools" },
        { type: "mcp_server", label: "MCP Server", desc: "Context servers" },
        { type: "settings", label: "Settings", desc: "Shared config" },
    ];

    const reset = () => {
        setStep('type');
        setSelectedType(null);
        setOpen(false);
    };

    return (
        <Popover open={open} onOpenChange={(o) => { if (!o) reset(); else setOpen(true); }}>
            <PopoverTrigger asChild>
                <Button type="button" variant="outline" size="sm" className="h-7 w-7 p-0 rounded-full bg-muted hover:bg-primary hover:text-white transition-colors border-dashed border-zinc-400" disabled={disabled}>
                    <Plus size={14} />
                </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[300px] p-0" align="start">
                {step === 'type' ? (
                    <Command>
                        <CommandInput placeholder="Select option type..." />
                        <CommandList>
                            <CommandGroup heading="Option Type">
                                {typeOptions.map((opt) => (
                                    <CommandItem key={opt.type} onSelect={() => { setSelectedType(opt.type as any); setStep('block'); }}>
                                        <div className="flex flex-col">
                                            <span className="font-bold">{opt.label}</span>
                                            <span className="text-xs text-muted-foreground">{opt.desc}</span>
                                        </div>
                                    </CommandItem>
                                ))}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                ) : (
                    <Command>
                        <CommandInput placeholder={`Select ${selectedType}...`} />
                        <CommandList>
                            <CommandEmpty>No blocks found.</CommandEmpty>
                            <CommandGroup heading={selectedType?.toUpperCase()}>
                                {blocks.filter((b: ConfigBlock) => b.type === selectedType).map((b: ConfigBlock) => {
                                    let desc = "";
                                    try {
                                        const c = JSON.parse(b.content);
                                        // Try to find a description or relevant detail
                                        desc = c.description || c.desc || (typeof c === 'string' ? c : "");
                                        if (!desc && selectedType === 'extension') desc = c.source || c.ref;
                                        if (!desc && selectedType === 'mcp_server') desc = c.command;
                                    } catch {
                                        desc = b.content.length > 50 ? b.content.substring(0, 50) + "..." : b.content;
                                    }

                                    return (
                                        <CommandItem key={b.id} value={b.name} onSelect={() => {
                                            onAdd(selectedType as ConfigBlockType, b);
                                            reset();
                                        }}>
                                            <div className="flex flex-col">
                                                <span>{b.name}</span>
                                                {desc && <span className="text-xs text-muted-foreground line-clamp-1">{desc}</span>}
                                            </div>
                                        </CommandItem>
                                    );
                                })}
                            </CommandGroup>
                        </CommandList>
                    </Command>
                )}
            </PopoverContent>
        </Popover>
    );

}