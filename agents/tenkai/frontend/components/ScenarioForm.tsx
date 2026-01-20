"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input, TextArea, Select } from "@/components/ui/input";
import { AssetUploader } from "@/components/AssetUploader";
import { ValidationRule, ScenarioAsset } from "@/types/domain";
import { generateAcceptanceCriteria, syncAcceptanceCriteria, splitPrompt } from "@/lib/prompt";

export interface ScenarioFormProps {
    mode: 'create' | 'edit';
    initialData?: any;
    onSubmit: (formData: FormData) => Promise<void>;
    isLoading?: boolean;
    isLocked?: boolean;
}

export default function ScenarioForm({ mode, initialData, onSubmit, isLoading = false, isLocked = false }: ScenarioFormProps) {
    const router = useRouter();

    // Core
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [task, setTask] = useState(""); // Manual prompt part only
    const [taskMode, setTaskMode] = useState<'prompt' | 'github'>('prompt');

    // Assets & Links
    const [githubIssue, setGithubIssue] = useState("");
    const [githubTaskType, setGithubTaskType] = useState<'issue' | 'prompt'>('issue');
    const [assetType, setAssetType] = useState<'none' | 'folder' | 'files' | 'git' | 'create'>('none');
    const [gitUrl, setGitUrl] = useState("");
    const [gitRef, setGitRef] = useState("");
    const [assets, setAssets] = useState<ScenarioAsset[]>([]);

    // Validation
    const [validation, setValidation] = useState<ValidationRule[]>([]);
    const [newValType, setNewValType] = useState("test");
    const [newValTarget, setNewValTarget] = useState("");
    const [newValThreshold, setNewValThreshold] = useState("");
    const [newValInclude, setNewValInclude] = useState(true);
    const [newValStdin, setNewValStdin] = useState("");
    const [newValStdinDelay, setNewValStdinDelay] = useState("");
    const [newValOutput, setNewValOutput] = useState("");
    const [newValRegex, setNewValRegex] = useState("");
    const [editingIdx, setEditingIdx] = useState<number | null>(null);

    // Files
    const [files, setFiles] = useState<FileList | null>(null);
    const [fileName, setFileName] = useState("");
    const [fileContent, setFileContent] = useState("");

    // Environment
    const [envVars, setEnvVars] = useState<{ key: string, value: string }[]>([]);
    const [newEnvKey, setNewEnvKey] = useState("");
    const [newEnvValue, setNewEnvValue] = useState("");

    // Initialization Effect
    useEffect(() => {
        if (!initialData) return;

        setName(initialData.name || "");
        setDescription(initialData.description || "");

        // Split prompt logic
        if (initialData.task) {
            const { manual } = splitPrompt(initialData.task);
            setTask(manual);
        } else {
            setTask("");
        }

        // Backfill include_in_prompt for existing data
        const loadedVal = (initialData.validation || []).map((v: ValidationRule) => ({
            ...v,
            include_in_prompt: v.include_in_prompt !== undefined ? v.include_in_prompt : (v.type !== 'model')
        }));
        setValidation(loadedVal);

        setAssets(initialData.assets || []);

        if (initialData.env) {
            setEnvVars(Object.entries(initialData.env).map(([key, value]) => ({ key, value: String(value) })));
        }

        if (initialData.github_issue) {
            setTaskMode('github');
            setGithubIssue(initialData.github_issue);
            setGithubTaskType('issue');
        } else if (initialData.task) {
            setTaskMode('prompt');
        }

        if (initialData.assets && initialData.assets.length > 0) {
            const first = initialData.assets[0];
            if (first.type === 'git') {
                setAssetType('git');
                setGitUrl(first.source);
                setGitRef(first.ref || "");
            } else if (first.type === 'directory') {
                setAssetType('folder');
            } else if (first.type === 'file' && first.content === "") {
                setAssetType('folder');
            }
        }
    }, [initialData]);

    const addEnvVar = () => {
        if (!newEnvKey) return;
        setEnvVars([...envVars, { key: newEnvKey, value: newEnvValue }]);
        setNewEnvKey("");
        setNewEnvValue("");
    };

    const removeEnvVar = (idx: number) => {
        setEnvVars(envVars.filter((_, i) => i !== idx));
    };

    const toggleInclude = (idx: number) => {
        const newV = [...validation];
        newV[idx].include_in_prompt = !newV[idx].include_in_prompt;
        setValidation(newV);
    };

    const clearValForm = () => {
        setNewValTarget("");
        setNewValThreshold("");
        setNewValStdin("");
        setNewValStdinDelay("");
        setNewValOutput("");
        setNewValRegex("");
        setNewValInclude(newValType !== 'model');
        setEditingIdx(null);
    };

    const startEditValidation = (idx: number) => {
        const v = validation[idx];
        setEditingIdx(idx);
        setNewValType(v.type);
        setNewValInclude(v.include_in_prompt ?? true);

        if (v.type === 'command') {
            setNewValTarget(v.command || '');
            setNewValThreshold(v.expect_exit_code?.toString() || '');
            setNewValStdin(v.stdin || '');
            setNewValStdinDelay(v.stdin_delay || '');
            setNewValOutput(v.expect_output || '');
            setNewValRegex(v.expect_output_regex || '');
        } else if (v.type === 'model') {
            setNewValTarget(v.prompt || '');
        } else if (v.type === 'manual') {
            setNewValTarget(v.target || '');
        } else {
            setNewValTarget(v.target || './...');
            if (v.type === 'test') setNewValThreshold(v.min_coverage?.toString() || '');
            if (v.type === 'lint') setNewValThreshold(v.max_issues?.toString() || '');
        }
    };

    const addValidation = () => {
        // Validation check for empty fields
        if (newValType === 'model' && !newValTarget.trim()) {
            toast.error("AI Review instructions cannot be empty.");
            return;
        }

        const val: Partial<ValidationRule> = { type: newValType as any, include_in_prompt: newValInclude };

        if (newValType === 'command') {
            val.command = newValTarget;
            if (newValThreshold) val.expect_exit_code = parseInt(newValThreshold);
            if (newValStdin) val.stdin = newValStdin;
            if (newValStdinDelay) val.stdin_delay = newValStdinDelay;
            if (newValOutput) val.expect_output = newValOutput;
            if (newValRegex) val.expect_output_regex = newValRegex;
        } else if (newValType === 'model') {
            val.prompt = newValTarget;
        } else if (newValType === 'manual') {
            val.target = newValTarget;
        } else {
            val.target = newValTarget || "./...";
            if (newValType === 'test') val.min_coverage = parseFloat(newValThreshold) || 0;
            if (newValType === 'lint') val.max_issues = parseInt(newValThreshold) || 0;
        }

        if (editingIdx !== null) {
            // Update existing validation
            const newValidation = [...validation];
            newValidation[editingIdx] = val as ValidationRule;
            setValidation(newValidation);
            toast.success("Validation rule updated.");
        } else {
            // Add new validation
            setValidation([...validation, val as ValidationRule]);
        }

        clearValForm();
    };

    const removeValidation = (idx: number) => {
        setValidation(validation.filter((_, i) => i !== idx));
    };

    const handlePromptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            if (ev.target?.result) {
                setTask(ev.target.result as string);
            }
        };
        reader.readAsText(file);
    };

    const handleFormSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        let finalValidation = [...validation];

        // Auto-commit pending edits if user clicked Save while editing a rule
        if (editingIdx !== null) {
            const val: Partial<ValidationRule> = { type: newValType as any, include_in_prompt: newValInclude };

            if (newValType === 'command') {
                val.command = newValTarget;
                if (newValThreshold) val.expect_exit_code = parseInt(newValThreshold);
                if (newValStdin) val.stdin = newValStdin;
                if (newValStdinDelay) val.stdin_delay = newValStdinDelay;
                if (newValOutput) val.expect_output = newValOutput;
                if (newValRegex) val.expect_output_regex = newValRegex;
            } else if (newValType === 'model') {
                val.prompt = newValTarget;
            } else if (newValType === 'manual') {
                val.target = newValTarget;
            } else {
                val.target = newValTarget || "./...";
                if (newValType === 'test') val.min_coverage = parseFloat(newValThreshold) || 0;
                if (newValType === 'lint') val.max_issues = parseInt(newValThreshold) || 0;
            }
            finalValidation[editingIdx] = val as ValidationRule;
            toast.info("Applied pending rule changes.");
        }

        if (finalValidation.length === 0) {
            toast.error("Scenario must have at least one validation rule.");
            return;
        }

        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('validation', JSON.stringify(finalValidation));

        const envMap: Record<string, string> = {};
        envVars.forEach(e => { envMap[e.key] = e.value; });
        formData.append('env', JSON.stringify(envMap));

        // Combine Manual Task + Acceptance Criteria
        if (taskMode === 'prompt' || (taskMode === 'github' && githubTaskType === 'prompt')) {
            const combinedTask = syncAcceptanceCriteria(task, validation);
            formData.append('task', combinedTask); // API expects 'task' (or 'prompt' in create, handled by component user if needed? No, standard form uses 'task' or 'prompt' depending on endpoint, but let's check legacy code. create uses 'prompt', update uses 'task'. We might need to handle this discrepancy or normalize.)
            // Correction: Create API (POST /api/scenarios) expects 'prompt'. Update API (PUT /api/scenarios/[id]) expects 'task'.
            // Actually, let's look at `frontend/app/scenarios/new/page.tsx`:
            // formData.append('prompt', combinedTask);
            // And `frontend/app/scenarios/[id]/page.tsx`:
            // formData.append('task', combinedTask);

            // To be safe, we can append BOTH or rely on the parent to cleanup. BUT FormData is immutable-ish.
            // Let's standardise on passing both keys since backend likely looks for one. 
            // Or better, let's just use 'prompt' for create and 'task' for update?
            // Wait, the backend structs:
            // CreateScenarioRequest: Prompt string
            // UpdateScenarioRequest: Task string
            // I will append BOTH keys to the FormData to be safe, or conditionally based on mode.
            if (mode === 'create') {
                formData.append('prompt', combinedTask);
            } else {
                formData.append('task', combinedTask);
            }
        }

        if (taskMode === 'github' && githubTaskType === 'issue') {
            formData.append('github_issue', githubIssue);
        }

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
        } else if (assetType === 'create') {
            formData.append('file_name', fileName);
            formData.append('file_content', fileContent);
        }

        await onSubmit(formData);
    };

    return (
        <form onSubmit={handleFormSubmit} className="space-y-8">

            {/* 1. Details */}
            <Card>
                <CardHeader>
                    <CardTitle>Scenario Details</CardTitle>
                    <CardDescription>Core identity of the scenario</CardDescription>
                </CardHeader>
                <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="md:col-span-2">
                        <Input label="Display Name" value={name} onChange={(e) => setName(e.target.value)} required placeholder="e.g. Legacy Refactoring" />
                    </div>
                    <div className="md:col-span-2">
                        <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} placeholder="Briefly explain what this scenario tests..." />
                    </div>

                    <div>
                        <Select
                            label="Task Source"
                            value={taskMode}
                            onChange={(e) => {
                                const mode = e.target.value as any;
                                setTaskMode(mode);
                                if (mode === 'github') setAssetType('git');
                                else setAssetType('none');
                            }}
                            options={[
                                { value: 'prompt', label: 'Manual Prompt' },
                                { value: 'github', label: 'GitHub Issue' }
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
                                    { value: 'issue', label: 'Use Issue Body' },
                                    { value: 'prompt', label: 'Use Manual Prompt' }
                                ]}
                            />
                        </div>
                    )}
                    {taskMode === 'github' && (
                        <div className="md:col-span-2">
                            <Input
                                label="GitHub Issue URL"
                                value={githubIssue}
                                onChange={(e) => {
                                    const val = e.target.value;
                                    setGithubIssue(val);
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
                </CardContent>
            </Card>

            {/* 2. Prompt */}
            {(taskMode === 'prompt' || (taskMode === 'github' && githubTaskType === 'prompt')) && (
                <Card>
                    <CardHeader>
                        <CardTitle>Agent Prompt</CardTitle>
                        <CardDescription>Manual instructions for the agent (excluding automated criteria)</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex justify-end mb-2">
                            <div className="relative">
                                <input type="file" onChange={handlePromptUpload} className="absolute inset-0 opacity-0 cursor-pointer" accept=".md,.txt" />
                                <Button type="button" variant="outline" size="sm">Upload Text</Button>
                            </div>
                        </div>
                        <TextArea
                            label="Task Instructions"
                            value={task}
                            onChange={(e) => setTask(e.target.value)}
                            rows={12}
                            required
                            className="font-mono"
                            placeholder="# Task Objective..."
                        />
                    </CardContent>
                </Card>
            )}

            {/* 3. Assets */}
            <Card>
                <CardHeader>
                    <CardTitle>Scenario Assets</CardTitle>
                    <CardDescription>Files and code the agent will work with</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                    {taskMode === 'github' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 animate-in fade-in slide-in-from-top-2 duration-500">
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
                    ) : (
                        <AssetUploader
                            assetType={assetType}
                            setAssetType={setAssetType}
                            files={files}
                            setFiles={setFiles}
                            fileName={fileName}
                            setFileName={setFileName}
                            fileContent={fileContent}
                            setFileContent={setFileContent}
                            existingAssets={assets}
                        />
                    )}
                </CardContent>
            </Card>

            {/* 4. Environment */}
            <Card>
                <CardHeader>
                    <CardTitle>Scenario Environment</CardTitle>
                    <CardDescription>Environment variables exposed to the agent</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    <div className="space-y-2">
                        {envVars.map((e, i) => (
                            <div key={i} className="flex gap-4 items-center bg-card p-2 rounded border border-border">
                                <span className="font-mono text-emerald-600 dark:text-emerald-400">{e.key}</span>
                                <span className="text-muted-foreground">=</span>
                                <span className="font-mono text-body flex-1 truncate text-foreground">{e.value}</span>
                                <button type="button" onClick={() => removeEnvVar(i)} className="text-muted-foreground hover:text-destructive">✕</button>
                            </div>
                        ))}
                        {envVars.length === 0 && <p className="text-body opacity-30 italic">No environment variables defined.</p>}
                    </div>
                    <div className="flex gap-4 items-end">
                        <div className="w-1/3">
                            <Input label="Key" value={newEnvKey} onChange={(e) => setNewEnvKey(e.target.value)} placeholder="GEMINI_API_KEY" />
                        </div>
                        <div className="flex-1">
                            <Input label="Value" value={newEnvValue} onChange={(e) => setNewEnvValue(e.target.value)} placeholder="secret..." />
                        </div>
                        <div>
                            <Button type="button" variant="outline" onClick={addEnvVar}>Add Env</Button>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* 5. Validation Criteria */}
            <Card>
                <CardHeader>
                    <CardTitle>Validation Criteria</CardTitle>
                    <CardDescription>Automated rules for success and generated acceptance criteria</CardDescription>
                </CardHeader>
                <CardContent className="space-y-8">
                    {/* Rules List */}
                    <div className="space-y-4">
                        {validation.map((v, i) => (
                            <div
                                key={i}
                                className={`p-4 bg-card rounded border ${editingIdx === i ? 'border-primary' : 'border-border'}`}
                            >
                                <div className="flex justify-between items-start gap-4">
                                    <div className="flex-1 space-y-2">
                                        <div className="flex gap-3 items-center flex-wrap">
                                            <input
                                                type="checkbox"
                                                checked={!!v.include_in_prompt}
                                                onChange={() => toggleInclude(i)}
                                                className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-primary focus:ring-1 focus:ring-primary flex-shrink-0"
                                                title="Include in Acceptance Criteria"
                                            />
                                            <span className={`px-2 py-0.5 rounded font-bold uppercase text-xs ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : v.type === 'lint' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : v.type === 'model' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' : v.type === 'manual' ? 'bg-blue-500/10 text-blue-400' : 'bg-primary/10 text-primary'}`}>{v.type}</span>
                                            {v.include_in_prompt && <span className="text-[10px] text-muted-foreground bg-muted/30 px-1.5 py-0.5 rounded">in prompt</span>}
                                        </div>

                                        <div className="font-mono text-sm text-foreground bg-muted/20 p-2 rounded break-all">
                                            {v.type === 'command' ? v.command : v.type === 'model' ? v.prompt : v.target}
                                        </div>

                                        {v.type === 'command' && (
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                                                {v.expect_exit_code !== undefined && (
                                                    <div className="flex gap-2">
                                                        <span className="text-muted-foreground">Exit Code:</span>
                                                        <span className="font-mono text-foreground">{v.expect_exit_code}</span>
                                                    </div>
                                                )}
                                                {v.stdin && (
                                                    <div className="md:col-span-2">
                                                        <span className="text-muted-foreground">Stdin:</span>
                                                        <pre className="font-mono text-foreground bg-muted/30 p-2 rounded mt-1 text-xs whitespace-pre-wrap">{v.stdin}</pre>
                                                    </div>
                                                )}
                                                {v.stdin_delay && (
                                                    <div className="md:col-span-2">
                                                        <span className="text-muted-foreground">Stdin Delay:</span>
                                                        <span className="font-mono text-foreground bg-muted/30 px-2 py-1 rounded ml-2 text-xs">{v.stdin_delay}</span>
                                                    </div>
                                                )}
                                                {v.expect_output && (
                                                    <div className="md:col-span-2">
                                                        <span className="text-muted-foreground">Expected Output:</span>
                                                        <pre className="font-mono text-foreground bg-muted/30 p-2 rounded mt-1 text-xs whitespace-pre-wrap">{v.expect_output}</pre>
                                                    </div>
                                                )}
                                                {v.expect_output_regex && (
                                                    <div className="md:col-span-2">
                                                        <span className="text-muted-foreground">Expected Regex:</span>
                                                        <code className="font-mono text-foreground bg-muted/30 px-2 py-1 rounded ml-2">{v.expect_output_regex}</code>
                                                    </div>
                                                )}
                                            </div>
                                        )}

                                        {v.type === 'test' && v.min_coverage !== undefined && (
                                            <div className="text-sm">
                                                <span className="text-muted-foreground">Min Coverage:</span>
                                                <span className="font-mono text-foreground ml-2">{v.min_coverage}%</span>
                                            </div>
                                        )}
                                        {v.type === 'lint' && v.max_issues !== undefined && (
                                            <div className="text-sm">
                                                <span className="text-muted-foreground">Max Issues:</span>
                                                <span className="font-mono text-foreground ml-2">{v.max_issues}</span>
                                            </div>
                                        )}
                                    </div>

                                    <div className="flex gap-2 flex-shrink-0">
                                        <button
                                            type="button"
                                            onClick={() => startEditValidation(i)}
                                            className="text-muted-foreground hover:text-primary px-2 py-1 text-sm"
                                            title="Edit this validation"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            type="button"
                                            onClick={(e) => { e.stopPropagation(); removeValidation(i); }}
                                            className="text-muted-foreground hover:text-destructive px-2 py-1 text-sm"
                                            title="Delete this validation"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                        {validation.length === 0 && <p className="text-body opacity-30 italic">No validation rules defined.</p>}
                    </div>

                    <div className={`p-4 bg-muted/10 border rounded flex gap-6 items-start ${editingIdx !== null ? 'border-primary' : 'border-border'}`}>
                        {/* LEFT COLUMN: Main Inputs */}
                        <div className="flex-1 space-y-4">
                            {editingIdx !== null && (
                                <div className="absolute -mt-7 left-4 px-2 py-0.5 bg-primary text-primary-foreground text-xs font-bold rounded">
                                    Editing Rule #{editingIdx + 1}
                                </div>
                            )}

                            <div className="flex gap-4">
                                <div className="w-[140px]">
                                    <Select
                                        label="Type"
                                        value={newValType}
                                        onChange={(e) => {
                                            const t = e.target.value;
                                            setNewValType(t);
                                            setNewValInclude(t !== 'model');
                                        }}
                                        options={[
                                            { value: 'test', label: 'Unit Test' },
                                            { value: 'lint', label: 'Linter' },
                                            { value: 'command', label: 'Command' },
                                            { value: 'model', label: 'AI Review' },
                                            { value: 'manual', label: 'Manual Criteria' }
                                        ]}
                                    />
                                </div>
                                <div className="flex-1">
                                    {newValType === 'model' ? (
                                        <TextArea
                                            label="Review Instructions"
                                            placeholder="Prompt for an AI agent to evaluate the project."
                                            value={newValTarget}
                                            onChange={(e) => setNewValTarget(e.target.value)}
                                            rows={2}
                                        />
                                    ) : newValType === 'manual' ? (
                                        <Input
                                            label="Criteria Text"
                                            placeholder="e.g. The user interface must be responsive"
                                            value={newValTarget}
                                            onChange={(e) => setNewValTarget(e.target.value)}
                                        />
                                    ) : (
                                        <Input
                                            label={newValType === 'command' ? 'Command' : 'Target Path'}
                                            placeholder={newValType === 'command' ? 'echo "success"' : './...'}
                                            value={newValTarget}
                                            onChange={(e) => setNewValTarget(e.target.value)}
                                        />
                                    )}
                                </div>
                            </div>

                            {newValType === 'command' ? (
                                <div className="space-y-4 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <TextArea
                                        label="Stdin (optional)"
                                        placeholder="Input to pipe to the command. Line breaks are preserved."
                                        value={newValStdin}
                                        onChange={(e) => setNewValStdin(e.target.value)}
                                        rows={4}
                                    />

                                    <Input
                                        label="Expect Output (substring)"
                                        placeholder="success"
                                        value={newValOutput}
                                        onChange={(e) => setNewValOutput(e.target.value)}
                                    />

                                    <Input
                                        label="Expect Output (regex)"
                                        placeholder="^hello.*"
                                        value={newValRegex}
                                        onChange={(e) => setNewValRegex(e.target.value)}
                                    />
                                </div>
                            ) : null}

                            {/* Test/Lint shared inputs */}
                            {newValType !== 'model' && newValType !== 'manual' && newValType !== 'command' && (
                                <div className="w-[100px]">
                                    <Input
                                        label={newValType === 'test' ? 'Min Cov' : 'Max Issues'}
                                        placeholder="0"
                                        value={newValThreshold}
                                        onChange={(e) => setNewValThreshold(e.target.value)}
                                    />
                                </div>
                            )}
                        </div>

                        {/* RIGHT COLUMN: Actions & Secondary Inputs */}
                        <div className="w-[200px] flex flex-col gap-4">
                            <Button type="button" variant={editingIdx !== null ? "default" : "secondary"} onClick={addValidation} className="w-full">
                                {editingIdx !== null ? 'Update Rule' : 'Add Rule'}
                            </Button>

                            <Button type="button" variant="ghost" size="sm" onClick={clearValForm} className="text-[10px] h-6 w-full">
                                {editingIdx !== null ? 'Cancel Edit' : 'Clear'}
                            </Button>

                            <label className="flex items-center gap-2 cursor-pointer pt-2" title="Include in Generated Acceptance Criteria">
                                <input
                                    type="checkbox"
                                    checked={newValInclude}
                                    onChange={(e) => setNewValInclude(e.target.checked)}
                                    className="w-3 h-3 rounded border-zinc-700 bg-zinc-800 text-primary focus:ring-1 focus:ring-primary"
                                />
                                <span className="text-[9px] uppercase font-bold text-muted-foreground leading-none">Add to Acceptance Criteria</span>
                            </label>

                            {/* Extra inputs moved here for Command type */}
                            {newValType === 'command' && (
                                <div className="space-y-4 pt-4 border-t border-border animate-in fade-in">
                                    <Input
                                        label="Exit Code"
                                        placeholder="0"
                                        value={newValThreshold}
                                        onChange={(e) => setNewValThreshold(e.target.value)}
                                    />
                                    <Input
                                        label="Stdin Delay"
                                        placeholder="500ms"
                                        value={newValStdinDelay}
                                        onChange={(e) => setNewValStdinDelay(e.target.value)}
                                    />
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Generated AC Preview */}
                    <div className="mt-8 pt-6 border-t border-border">
                        <h4 className="text-sm font-bold uppercase tracking-widest text-muted-foreground mb-4">Generated Acceptance Criteria</h4>
                        <div className="bg-[#1e1e20] p-4 rounded-md font-mono text-sm text-zinc-300 border border-zinc-800 whitespace-pre-wrap">
                            {validation.length > 0 ? (generateAcceptanceCriteria(validation) || <span className="text-zinc-600 italic">No active criteria selected.</span>) : <span className="text-zinc-600 italic">No criteria generated yet.</span>}
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-2">This block will be automatically appended to the agent prompt.</p>
                    </div>
                </CardContent>
            </Card>

            <div className="flex justify-end gap-4 pb-20">
                <Link href="/scenarios">
                    <Button variant="ghost">Cancel</Button>
                </Link>
                <Button type="submit" variant="default" size="lg" isLoading={isLoading} disabled={isLocked || isLoading}>
                    {mode === 'edit' ? 'Save Changes' : 'Create Scenario'}
                </Button>
            </div>
        </form>
    );
}
