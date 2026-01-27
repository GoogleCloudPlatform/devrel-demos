
import { useState } from "react";
import { ConfigBlock, ConfigBlockType } from "@/types/domain";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/input"; // Helper we used in BlockSelector
import { Check, Copy, X, Search, Plus } from "lucide-react";
import { toast } from "sonner";
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


export interface AlternativeCardProps {
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

export default function AlternativeCard({
    alt, index, blocks, isControl, onUpdate, onSetControl, onDelete, onDuplicate,
    getAgentName, getBlockName, isLocked
}: AlternativeCardProps) {
    // Generate thematic color style if locked (Report Mode)
    const colorStyle = (() => {
        if (!isLocked) return {}; // Default styling for edit mode

        const altColors = [
            "border-indigo-500/50 bg-indigo-500/5",
            "border-emerald-500/50 bg-emerald-500/5",
            "border-amber-500/50 bg-amber-500/5",
            "border-rose-500/50 bg-rose-500/5",
            "border-cyan-500/50 bg-cyan-500/5",
            "border-violet-500/50 bg-violet-500/5",
            "border-orange-500/50 bg-orange-500/5",
            "border-lime-500/50 bg-lime-500/5",
            "border-fuchsia-500/50 bg-fuchsia-500/5",
            "border-sky-500/50 bg-sky-500/5",
        ];

        const containerClass = isControl
            ? 'border-indigo-500/50 shadow-[0_0_20px_-10px_#6366f1] bg-indigo-900/10'
            : altColors[index % altColors.length];

        return { className: containerClass };
    })();

    return (
        <div className={cn("bg-card border rounded-xl p-6 shadow-sm hover:shadow-md transition-shadow", isLocked ? colorStyle.className : "border-border")}>
            {/* Header Row */}
            <div className="flex items-center gap-4 mb-4">
                <Input
                    value={alt.name}
                    onChange={(e) => onUpdate('name', e.target.value)}
                    className="font-bold flex-1 bg-transparent"
                    placeholder="Alternative Name"
                    disabled={isLocked}
                />

                <div
                    className={cn(
                        "flex items-center gap-2 cursor-pointer px-3 py-2 rounded-md border transition-colors select-none",
                        isControl ? "bg-primary/10 border-primary text-primary" : "bg-muted hover:bg-muted/80 border-transparent text-muted-foreground",
                        isLocked && "cursor-default pointer-events-none opacity-100" // Ensure opacity is full in read-only
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
                    {!isLocked && (
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
                    )}
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
        skill: "bg-sky-500/10 text-sky-600 dark:text-sky-400 border-sky-200 dark:border-sky-800",
        extension: "bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border-indigo-200 dark:border-indigo-800",
        mcp_server: "bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-200 dark:border-orange-800",
        settings: "bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800"
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

    if (disabled) {
        return (
            <Button
                type="button"
                variant="outline"
                role="combobox"
                className="w-full justify-between font-normal opacity-100 cursor-default"
                disabled={true}
            >
                <span className={cn(!valueContent && !required ? "text-muted-foreground italic" : "")}>
                    {displayValue}
                </span>
                {/* Could hide search icon when disabled */}
            </Button>
        )
    }

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
