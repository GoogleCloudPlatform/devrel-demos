'use client';

import { useState, useEffect } from "react";
import { ConfigBlock, ConfigBlockType } from "@/types/domain";
import { toast } from "sonner";
import { Plus, Trash2, Edit2, Copy, X } from "lucide-react";
import { Input, TextArea, Select } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function LibraryPage() {
    const [blocks, setBlocks] = useState<ConfigBlock[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<ConfigBlockType>("agent");
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    const [editingBlock, setEditingBlock] = useState<ConfigBlock | null>(null);

    const fetchBlocks = async () => {
        try {
            const res = await fetch("/api/blocks");
            if (!res.ok) throw new Error("Failed to fetch blocks");
            const data = await res.json();
            setBlocks(data || []);
        } catch (err) {
            console.error(err);
            toast.error("Failed to load library");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchBlocks();
    }, []);

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this block?")) return;

        try {
            const res = await fetch(`/api/blocks/${id}`, { method: "DELETE" });
            if (!res.ok) throw new Error("Failed to delete block");
            toast.success("Block deleted");
            fetchBlocks();
        } catch (err) {
            console.error(err);
            toast.error("Failed to delete block");
        }
    };

    const handleOpenCreate = () => {
        setEditingBlock(null);
        setCopiedData(null);
        setIsDialogOpen(true);
    };

    const handleOpenEdit = (block: ConfigBlock) => {
        setEditingBlock(block);
        setCopiedData(null);
        setIsDialogOpen(true);
    };

    const handleCloseDialog = () => {
        setIsDialogOpen(false);
        setEditingBlock(null);
    };

    const handleCopy = (block: ConfigBlock) => {
        const copiedBlock = {
            ...block,
            id: 0, // Should be ignored/reset by create logic
            name: `Copy of ${block.name}`,
        };
        setEditingBlock(null); // Ensure we are in create mode
        // But we want to pre-fill the form. 
        // My simple dialog logic relies on `editingBlock` for "edit mode".
        // Let's change the dialog to accept `initialValues` separately from `editingBlock` (which implies ID existence).
        // Or simpler: pass the copied data as `editingBlock` but strip the ID before saving? 
        // No, `editingBlock` implies PUT.

        // Let's add a robust solution:
        setEditingBlock(null); // Reset ID tracking
        // We need a way to pass data to the create dialog.
        // Let's add a new state `overrideInitialData` or similar.
        // Or just repurpose the Dialog props.

        // Actually, let's keep it simple: We open the dialog in Create mode, but we need to pass the content.
        // The current structure `BlockDialog({ initialData, ... })` uses initialData for both edit reference AND form init.
        // If I pass a mock object with id=0, my `handleSave` logic needs to check ID presence effectively.
        // handleSave checks `editingBlock` state variable, not the form data ID.
        // So if I `setEditingBlock(null)` but find a way to pass the *data*, it's a create.

        // Let's refactor `isDialogOpen` to be cleaner or simply:
        setCopiedData({ ...block, name: `Copy of ${block.name}` });
        setIsDialogOpen(true);
    };

    // New state for copy
    const [copiedData, setCopiedData] = useState<ConfigBlock | null>(null);

    const handleSave = async (data: { name: string; type: ConfigBlockType; content: string }) => {
        try {
            // If editingBlock is set, it's an update.
            const url = editingBlock ? `/api/blocks/${editingBlock.id}` : "/api/blocks";
            const method = editingBlock ? "PUT" : "POST";

            const res = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.error || "Failed to save block");
            }

            toast.success(`Block ${editingBlock ? "updated" : "created"} successfully`);
            handleCloseDialog();
            fetchBlocks();
        } catch (err: any) {
            console.error(err);
            toast.error(err.message || "Failed to save block");
        }
    };

    const filteredBlocks = blocks.filter(b => b.type === activeTab);

    return (
        <div className="p-6 space-y-6 max-w-7xl mx-auto relative">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-black italic tracking-tight text-foreground mb-2">Library</h1>
                    <p className="text-muted-foreground">Manage reusable configuration blocks for your experiments.</p>
                </div>
                <Button onClick={handleOpenCreate} className="flex items-center gap-2">
                    <Plus size={16} />
                    <span>Create New</span>
                </Button>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 border-b border-border overflow-x-auto">
                {(["agent", "system_prompt", "context", "settings", "mcp_server", "extension", "skill"] as ConfigBlockType[]).map((type) => (
                    <button
                        key={type}
                        onClick={() => setActiveTab(type)}
                        className={`px-4 py-2 border-b-2 font-medium text-sm transition-colors whitespace-nowrap ${activeTab === type
                            ? "border-primary text-primary"
                            : "border-transparent text-muted-foreground hover:text-foreground"
                            }`}
                    >
                        {formatType(type)}
                    </button>
                ))}
            </div>

            {/* Content */}
            {loading ? (
                <div className="py-12 text-center text-muted-foreground">Loading...</div>
            ) : filteredBlocks.length === 0 ? (
                <div className="py-12 text-center border border-dashed border-border rounded-lg bg-card/50">
                    <p className="text-muted-foreground">No blocks found for this type.</p>
                    <Button variant="link" onClick={handleOpenCreate}>Create your first {formatType(activeTab)} block</Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredBlocks.map((block) => (
                        <div key={block.id} className="p-4 rounded-lg border border-border bg-card hover:border-primary/50 transition-colors group flex flex-col h-full">
                            <div className="flex items-start justify-between mb-2">
                                <h3 className="font-bold text-lg text-card-foreground truncate pr-2" title={block.name}>{block.name}</h3>
                                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0">
                                    <button
                                        onClick={() => handleOpenEdit(block)}
                                        className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-foreground transition-colors"
                                    >
                                        <Edit2 size={14} />
                                    </button>
                                    <button
                                        onClick={() => handleCopy(block)}
                                        className="p-1.5 hover:bg-muted rounded text-muted-foreground hover:text-blue-400 transition-colors"
                                        title="Duplicate"
                                    >
                                        <Copy size={14} />
                                    </button>
                                    <button
                                        onClick={() => handleDelete(block.id)}
                                        className="p-1.5 hover:bg-red-500/10 rounded text-muted-foreground hover:text-red-500 transition-colors"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </div>
                            <div className="flex-1 bg-muted/30 p-3 rounded text-xs font-mono text-muted-foreground overflow-hidden">
                                <pre className="whitespace-pre-wrap break-all line-clamp-[8]">{block.content}</pre>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Dialog Overlay */}
            {isDialogOpen && (
                <div className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-center justify-center p-4">
                    <div
                        className="bg-card w-full max-w-lg border border-border rounded-lg shadow-lg flex flex-col max-h-[90vh]"
                        role="dialog"
                    >
                        <BlockDialog
                            initialData={editingBlock || copiedData}
                            activeTab={activeTab} // Default type for new blocks
                            onClose={handleCloseDialog}
                            onSave={handleSave}
                        />
                    </div>
                </div>
            )}
        </div>
    );
}

function formatType(type: string) {
    return type.split("_").map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

interface BlockDialogProps {
    initialData: ConfigBlock | null;
    activeTab: ConfigBlockType;
    onClose: () => void;
    onSave: (data: { name: string; type: ConfigBlockType; content: string }) => Promise<void>;
}

function BlockDialog({ initialData, activeTab, onClose, onSave }: BlockDialogProps) {
    const [name, setName] = useState(initialData?.name || "");
    const [type, setType] = useState<ConfigBlockType>(initialData?.type || activeTab);
    const [content, setContent] = useState(initialData?.content || "");

    // Structured state for Extensions and Skills
    const [structuredData, setStructuredData] = useState<any>({});
    const [useStructured, setUseStructured] = useState(true);

    const [loading, setLoading] = useState(false);

    // Reset state when initialData changes or dialog opens
    useEffect(() => {
        setName(initialData?.name || "");
        setType(initialData?.type || activeTab);
        const rawContent = initialData?.content || "";
        setContent(rawContent);

        // Parse content for structured editing if applicable
        if ((type === "extension" || type === "skill") && rawContent) {
            try {
                const parsed = JSON.parse(rawContent);
                setStructuredData(parsed);
                setUseStructured(true);
            } catch (e) {
                // Formatting error, fallback to raw
                setUseStructured(false);
            }
        } else {
            // Defaults for new blocks
            if ((type === "extension" || type === "skill") && !rawContent) {
                setUseStructured(true);
                if (type === "extension") {
                    setStructuredData({ name: "", source: "", ref: "", mode: "install", auto_update: false, consent: true, pre_release: false });
                } else {
                    setStructuredData({ name: "", source: "", path: "", scope: "user" });
                }
            } else {
                setUseStructured(false);
            }
        }
    }, [initialData, activeTab]);

    // Keep structuredData and content in sync when type changes for new blocks
    useEffect(() => {
        if (!initialData && (type === "extension" || type === "skill")) {
            setUseStructured(true);
            if (type === "extension") {
                const def = { name: "", source: "", ref: "", mode: "install", auto_update: false, consent: true, pre_release: false };
                setStructuredData(def);
                setContent(JSON.stringify(def, null, 2));
            } else {
                const def = { name: "", source: "", path: "", scope: "user" };
                setStructuredData(def);
                setContent(JSON.stringify(def, null, 2));
            }
        } else if (!initialData) {
            setUseStructured(false);
            // Other defaults...
            if (type === "agent") {
                setContent(JSON.stringify({ command: "gemini", args: ["run"], env: {} }, null, 2));
            }
        }
    }, [type]);

    const handleStructuredChange = (key: string, value: any) => {
        const newData = { ...structuredData, [key]: value };
        // Sync name if it's the extension name (special case: block name vs extension name in json? usually same)
        // Actually, we keep block name separate from internal name, but often they match.
        // Let's just update the internal JSON structure.
        if (key === "name" && !name) {
            setName(value);
        }
        setStructuredData(newData);
        setContent(JSON.stringify(newData, null, 2));
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        await onSave({ name, type, content });
        setLoading(false);
    };

    const renderStructuredForm = () => {
        if (type === "extension") {
            return (
                <div className="space-y-4 border p-4 rounded bg-muted/10">
                    <h3 className="font-semibold mb-2">Extension Configuration</h3>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Select
                            label="Installation Mode"
                            value={structuredData.mode || "install"}
                            onChange={(e) => handleStructuredChange("mode", e.target.value)}
                            options={[
                                { value: "install", label: "Install (Git/Registry)" },
                                { value: "link", label: "Link (Local Dev)" }
                            ]}
                        />
                        <Input label="Source (URL or Path)" value={structuredData.source || ""} onChange={(e) => handleStructuredChange("source", e.target.value)} placeholder={structuredData.mode === "link" ? "/absolute/path/to/extension" : "https://github.com/owner/repo"} required />
                    </div>

                    {structuredData.mode !== "link" && (
                        <>
                            <div className="flex gap-4">
                                <div className="flex-1">
                                    <Input label="Ref (Git Tag/Branch)" value={structuredData.ref || ""} onChange={(e) => handleStructuredChange("ref", e.target.value)} placeholder="main" />
                                </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4 pt-2">
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={structuredData.auto_update || false} onChange={(e) => handleStructuredChange("auto_update", e.target.checked)} className="w-4 h-4" />
                                    <span className="text-sm">Auto Update</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={structuredData.consent || false} onChange={(e) => handleStructuredChange("consent", e.target.checked)} className="w-4 h-4" />
                                    <span className="text-sm">Consent (Security)</span>
                                </label>
                                <label className="flex items-center gap-2 cursor-pointer">
                                    <input type="checkbox" checked={structuredData.pre_release || false} onChange={(e) => handleStructuredChange("pre_release", e.target.checked)} className="w-4 h-4" />
                                    <span className="text-sm">Pre-Release</span>
                                </label>
                            </div>
                        </>
                    )}
                </div>
            );
        }
        if (type === "skill") {
            return (
                <div className="space-y-4 border p-4 rounded bg-muted/10">
                    <h3 className="font-semibold mb-2">Skill Configuration</h3>
                    <Input label="Skill Name (Internal)" value={structuredData.name || ""} onChange={(e) => handleStructuredChange("name", e.target.value)} placeholder="my-skill" />
                    <Input label="Source (URL/Zip/Path)" value={structuredData.source || ""} onChange={(e) => handleStructuredChange("source", e.target.value)} placeholder="https://github.com/..." required />
                    <Input label="Subpath (Optional)" value={structuredData.path || ""} onChange={(e) => handleStructuredChange("path", e.target.value)} placeholder="skills/my-skill" />

                    <Select label="Scope" value={structuredData.scope || "user"} onChange={(e) => handleStructuredChange("scope", e.target.value)} options={[{ value: "user", label: "User (Global)" }, { value: "workspace", label: "Workspace (Project)" }]} />
                </div>
            )
        }
        return null;
    };

    return (
        <form onSubmit={handleSubmit} className="flex flex-col h-full">
            <div className="flex items-center justify-between p-4 border-b border-border">
                <h2 className="text-lg font-bold">{initialData ? "Edit Block" : "Create Block"}</h2>
                <button type="button" onClick={onClose} className="text-muted-foreground hover:text-foreground">
                    <X size={20} />
                </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto flex-1">
                <Input
                    label="Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Default Python Agent"
                    required
                />

                <Select
                    label="Type"
                    value={type}
                    onChange={(e) => setType(e.target.value as ConfigBlockType)}
                    options={[
                        { value: "agent", label: "Agent" },
                        { value: "system_prompt", label: "System Prompt" },
                        { value: "context", label: "Context File" },
                        { value: "settings", label: "Settings (JSON)" },
                        { value: "mcp_server", label: "MCP Server" },
                        { value: "extension", label: "Extension" },
                        { value: "skill", label: "Skill" },
                    ]}
                    // Disable type change if editing? Often better to lock it.
                    disabled={!!initialData}
                />

                {(type === "extension" || type === "skill") && (
                    <div className="flex justify-end">
                        <button type="button" onClick={() => setUseStructured(!useStructured)} className="text-xs text-primary hover:underline">
                            {useStructured ? "Switch to Raw JSON" : "Switch to Form"}
                        </button>
                    </div>
                )}

                {useStructured && (type === "extension" || type === "skill") ? (
                    renderStructuredForm()
                ) : (
                    <>
                        <TextArea
                            label="Content"
                            value={content}
                            onChange={(e) => setContent(e.target.value)}
                            rows={12}
                            className="font-mono text-sm leading-relaxed"
                            placeholder="Enter block configuration..."
                            required
                        />
                        <p className="text-xs text-muted-foreground">
                            {type === "agent" && "JSON object with 'command', 'args', 'env'."}
                            {type === "mcp_server" && "JSON object with 'command', 'args'."}
                            {type === "extension" && "JSON with 'name', 'source', 'mode', 'ref', etc."}
                            {type === "skill" && "JSON object with 'name', 'source' (URL/Path), 'path' (opt subpath), 'scope'."}
                            {type === "settings" && "JSON object for settings.json."}
                            {(type === "system_prompt" || type === "context") && "Plain text or Markdown content."}
                        </p>
                    </>
                )}
            </div>

            <div className="p-4 border-t border-border flex justify-end gap-3 bg-muted/10">
                <Button type="button" variant="ghost" onClick={onClose}>Cancel</Button>
                <Button type="submit" isLoading={loading}>{initialData ? "Update" : "Create"}</Button>
            </div>
        </form>
    );
}
