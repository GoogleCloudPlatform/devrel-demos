'use client';

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input, TextArea, Select } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";

export default function NewScenarioPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);

    // Core
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [task, setTask] = useState("");
    const [taskMode, setTaskMode] = useState<'prompt' | 'github'>('prompt');
    // Assets & Links
    const [githubIssue, setGithubIssue] = useState("");
    const [githubTaskType, setGithubTaskType] = useState<'issue' | 'prompt'>('issue');
    const [assetType, setAssetType] = useState<'none' | 'folder' | 'files' | 'git'>('none');
    const [gitUrl, setGitUrl] = useState("");
    const [gitRef, setGitRef] = useState("");

    const [files, setFiles] = useState<FileList | null>(null);

    // Validation
    const [validation, setValidation] = useState<any[]>([
        { type: "test", target: "./...", min_coverage: 70.0 },
        { type: "lint", target: "./...", max_issues: 0 }
    ]);
    const [newValType, setNewValType] = useState("test");
    const [newValTarget, setNewValTarget] = useState("");
    const [newValThreshold, setNewValThreshold] = useState("");

    const addValidation = () => {
        const val: any = { type: newValType };

        if (newValType === 'command') {
            val.command = newValTarget; // Using target input for command string
            val.expected_exit_code = parseInt(newValThreshold) || 0;
        } else {
            val.target = newValTarget || "./...";
            if (newValType === 'test') val.min_coverage = parseFloat(newValThreshold) || 0;
            if (newValType === 'lint') val.max_issues = parseInt(newValThreshold) || 0;
        }

        setValidation([...validation, val]);
        setNewValTarget("");
        setNewValThreshold("");
    };
    const editValidation = (idx: number) => {
        const val = validation[idx];
        setNewValType(val.type);
        if (val.type === 'command') {
            setNewValTarget(val.command);
            setNewValThreshold(val.expected_exit_code?.toString() || "");
        } else {
            setNewValTarget(val.target);
            if (val.type === 'test') setNewValThreshold(val.min_coverage?.toString() || "");
            if (val.type === 'lint') setNewValThreshold(val.max_issues?.toString() || "");
        }
        removeValidation(idx);
    };

    const removeValidation = (idx: number) => {
        setValidation(validation.filter((_, i) => i !== idx));
    };

    const handlePromptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            if (ev.target?.result) setTask(ev.target.result as string);
        };
        reader.readAsText(file);
    };

    const handleSubmit = async (e: React.FormEvent) => {

        e.preventDefault();

        // Ensure at least one validation rule is present
        if (validation.length === 0) {
            alert("Scenario must have at least one validation rule. Experiments cannot be evaluated without success criteria.");
            return;
        }

        setLoading(true);

        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('validation', JSON.stringify(validation));

        // Task Logic
        if (taskMode === 'prompt' || (taskMode === 'github' && githubTaskType === 'prompt')) {
            formData.append('prompt', task);
        }
        if (taskMode === 'github' && githubTaskType === 'issue') {
            formData.append('github_issue', githubIssue);
        }
        // Map 'files' asset type to 'folder' for backend compatibility if backend expects 'folder' for file lists
        // Or if backend supports generic file list. Assuming 'folder' handles multi-part 'files'.
        if (assetType === 'files') {
            formData.append('asset_type', 'folder'); 
        } else {
            formData.append('asset_type', assetType);
        }

        if ((assetType === 'folder' || assetType === 'files') && files) {
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }
        } else if (assetType === 'git') {

            formData.append('git_url', gitUrl);
            formData.append('git_ref', gitRef);
        }

        try {
            const res = await fetch('/api/scenarios', {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                router.push('/scenarios');
            } else {
                alert("Failed to create scenario");
            }
        } catch (e) {
            alert("Error creating scenario");
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

            <form onSubmit={handleSubmit} className="space-y-8">
                <Card title="Scenario Configuration">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="md:col-span-2">
                            <Input label="Display Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Legacy Refactoring" />
                        </div>
                        <div className="md:col-span-2">
                            <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Briefly explain what this scenario tests..." />
                        </div>

                        {/* Task Mode Selection */}
                        <div>
                            <Select
                                label="Task Source"
                                value={taskMode}
                                onChange={(e) => {
                                    const mode = e.target.value as any;
                                    setTaskMode(mode);
                                    if (mode === 'github') {
                                        setAssetType('git');
                                    } else {
                                        setAssetType('none');
                                    }
                                }}
                                options={[
                                    { value: 'prompt', label: 'Prompt' },
                                    { value: 'github', label: 'GitHub' }
                                ]}
                            />
                        </div>

                        {taskMode === 'github' && (
                            <div className="animate-in fade-in slide-in-from-left-2 duration-300">
                                <Select
                                    label="Content Source"
                                    value={githubTaskType}
                                    onChange={(e) => setGithubTaskType(e.target.value as any)}
                                    options={[
                                        { value: 'issue', label: 'Issue' },
                                        { value: 'prompt', label: 'Prompt' }
                                    ]}
                                />
                            </div>
                        )}

                        {taskMode === 'github' && (
                            <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-8 animate-in fade-in slide-in-from-top-2 duration-500">
                                <Input
                                    label="Repository URL"
                                    value={gitUrl}
                                    onChange={(e) => setGitUrl(e.target.value)}
                                    required
                                    placeholder="https://github.com/org/repo.git"
                                />
                                <Input
                                    label="Ref / Branch / Tag"
                                    value={gitRef}
                                    onChange={(e) => setGitRef(e.target.value)}
                                    placeholder="main"
                                />
                            </div>
                        )}
                    </div>
                </Card>

                <Card title="Task Definition">
                    {/* Rendering Logic - Input Only */}
                    {(taskMode === 'prompt' || (taskMode === 'github' && githubTaskType === 'prompt')) ? (
                        <div className="space-y-4 animate-in fade-in duration-300">
                            <div className="flex justify-between items-center">
                                <p className="opacity-50 text-body">This task prompt will be presented to the agent. Be specific about goals and constraints.</p>
                                <div className="relative">
                                    <input type="file" onChange={handlePromptUpload} className="absolute inset-0 opacity-0 cursor-pointer" accept=".md,.txt" />
                                    <Button variant="outline" size="sm">Upload PROMPT.md</Button>
                                </div>
                            </div>
                            <TextArea
                                label="Agent Prompt / Task"
                                value={task}
                                onChange={(e) => setTask(e.target.value)}
                                rows={12}
                                required
                                className="font-mono"
                                placeholder="# Task Context..."
                            />
                        </div>
                    ) : (
                        <div className="space-y-4 animate-in fade-in duration-300">
                            <p className="opacity-50 text-body">The agent will be initialized with the content of the specified GitHub issue.</p>
                            <Input
                                label="GitHub Issue URL"
                                value={githubIssue}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    setGithubIssue(val);
                                    // Try to infer git url
                                    if (val.includes('github.com') && val.includes('/issues/')) {
                                        const repoPart = val.split('/issues/')[0];
                                        setGitUrl(repoPart + '.git');
                                    }
                                }}
                                required
                                placeholder="https://github.com/owner/repo/issues/123"
                            />
                        </div>
                    )}
                </Card>

                {taskMode === 'prompt' && (
                    <Card title="Workspace Assets">
                        <div className="space-y-6">
                            <div className="flex gap-4 border-b border-[#27272a] pb-4">
                                <button
                                    type="button"
                                    onClick={() => setAssetType('none')}
                                    className={`px-4 py-2 rounded font-bold text-body transition-colors ${assetType === 'none' ? 'bg-[#27272a] text-[#f4f4f5]' : 'text-[#71717a] hover:text-[#f4f4f5]'}`}
                                >
                                    Empty Workspace
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setAssetType('folder'); setFiles(null); }}
                                    className={`px-4 py-2 rounded font-bold text-body transition-colors ${assetType === 'folder' ? 'bg-[#27272a] text-[#f4f4f5]' : 'text-[#71717a] hover:text-[#f4f4f5]'}`}
                                >
                                    Upload Folder
                                </button>
                                <button
                                    type="button"
                                    onClick={() => { setAssetType('files'); setFiles(null); }}
                                    className={`px-4 py-2 rounded font-bold text-body transition-colors ${assetType === 'files' ? 'bg-[#27272a] text-[#f4f4f5]' : 'text-[#71717a] hover:text-[#f4f4f5]'}`}
                                >
                                    Upload Files
                                </button>
                            </div>

                            {(assetType === 'folder' || assetType === 'files') && (
                                <div className="panel p-6 border-dashed bg-[#09090b] flex flex-col items-center justify-center text-center relative overflow-hidden group">
                                    <div className="text-2xl mb-2 grayscale opacity-50">{assetType === 'folder' ? '📂' : '📄'}</div>
                                    <p className="text-body font-bold text-[#6366f1] uppercase tracking-widest hover:text-[#818cf8]">
                                        {assetType === 'folder' ? 'Click to Select Folder' : 'Click to Select Files'}
                                    </p>
                                    <input
                                        type="file"
                                        className="absolute opacity-0 w-full h-full cursor-pointer inset-0 z-10"
                                        {...(assetType === 'folder' ? { webkitdirectory: "", directory: "" } as any : { multiple: true })}
                                        onChange={(e) => setFiles(e.target.files)}
                                    />
                                    <p className="text-body font-mono opacity-50 mt-2">
                                        {files ? `${files.length} items selected` : (assetType === 'folder' ? "Drag folder here or click" : "Drag files here or click")}
                                    </p>
                                </div>
                            )}
                        </div>
                    </Card>
                )}

                <Card title="Validation Rules">
                    <div className="space-y-6">
                        <div className="space-y-3">
                            {validation.map((v, i) => (
                                <div 
                                    key={i} 
                                    className="flex justify-between items-center p-3 bg-[#161618] rounded border border-[#27272a] cursor-pointer hover:border-indigo-500/50 transition-colors group"
                                    onClick={() => editValidation(i)}
                                    title="Click to edit"
                                >
                                    <div className="flex gap-4 items-center">
                                        <span className={`px-2 py-0.5 rounded text-mono font-bold uppercase ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-400' : v.type === 'lint' ? 'bg-amber-500/10 text-amber-400' : 'bg-blue-500/10 text-blue-400'}`}>{v.type}</span>
                                        <span className="text-body font-mono">{v.type === 'command' ? v.command : v.target}</span>
                                        {v.min_coverage !== undefined && <span className="text-mono text-[#52525b]">min_cov: {v.min_coverage}%</span>}
                                        {v.max_issues !== undefined && <span className="text-mono text-[#52525b]">max_issues: {v.max_issues}</span>}
                                        {v.expected_exit_code !== undefined && <span className="text-mono text-[#52525b]">exit: {v.expected_exit_code}</span>}
                                    </div>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); removeValidation(i); }} className="text-[#52525b] hover:text-red-500 px-2">✕</button>
                                </div>
                            ))}
                            {validation.length === 0 && <p className="text-body opacity-30 italic">No validation rules defined.</p>}
                        </div>

                        <div className="p-4 bg-[#09090b] border border-[#27272a] rounded flex gap-4 items-end">
                            <div className="w-1/4">
                                <Select
                                    label="Type"
                                    value={newValType}
                                    onChange={(e) => setNewValType(e.target.value)}
                                    options={[
                                        { value: 'test', label: 'Unit Test' },
                                        { value: 'lint', label: 'Linter' },
                                        { value: 'command', label: 'Shell Command' }
                                    ]}
                                />
                            </div>
                            <div className="flex-1">
                                <Input
                                    label={newValType === 'command' ? 'Command' : 'Target Path'}
                                    placeholder={newValType === 'command' ? 'echo "success"' : './...'}
                                    value={newValTarget}
                                    onChange={(e) => setNewValTarget(e.target.value)}
                                />
                            </div>
                            <div className="w-1/4">
                                <Input
                                    label={newValType === 'test' ? 'Min Coverage' : newValType === 'lint' ? 'Max Issues' : 'Exit Code'}
                                    placeholder="0"
                                    value={newValThreshold}
                                    onChange={(e) => setNewValThreshold(e.target.value)}
                                />
                            </div>
                            <Button type="button" variant="outline" onClick={addValidation}>Add</Button>
                        </div>
                    </div>
                </Card>

                <div className="flex justify-end gap-4">
                    <Link href="/scenarios">
                        <Button variant="ghost">Cancel</Button>
                    </Link>
                    <Button type="submit" variant="default" size="lg" isLoading={loading}>
                        Initialize Scenario
                    </Button>
                </div>
            </form>
        </div>
    );
}