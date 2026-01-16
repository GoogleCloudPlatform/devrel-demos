"use client";

import React, { Suspense, useState, useEffect, use } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input, TextArea, Select } from "@/components/ui/input";
import { AssetUploader } from "@/components/AssetUploader";
import { Loader2 } from "lucide-react";
import { ValidationRule, ScenarioAsset } from "@/types/domain";
import { generateAcceptanceCriteria, splitPrompt, syncAcceptanceCriteria } from "@/lib/prompt";

function ScenarioEditorContent({ id }: { id: string }) {
    const router = useRouter();

    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);

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

    // Files
    const [files, setFiles] = useState<FileList | null>(null);
    const [fileName, setFileName] = useState("");
    const [fileContent, setFileContent] = useState("");

    // Environment
    const [envVars, setEnvVars] = useState<{ key: string, value: string }[]>([]);
    const [newEnvKey, setNewEnvKey] = useState("");
    const [newEnvValue, setNewEnvValue] = useState("");

    const addEnvVar = () => {
        if (!newEnvKey) return;
        setEnvVars([...envVars, { key: newEnvKey, value: newEnvValue }]);
        setNewEnvKey("");
        setNewEnvValue("");
    };

    const removeEnvVar = (idx: number) => {
        setEnvVars(envVars.filter((_, i) => i !== idx));
    };

    useEffect(() => {
        if (!id) {
            setFetching(false);
            return;
        }

        const fetchScenario = async () => {
            try {
                const res = await fetch(`/api/scenarios/${id}`);
                if (!res.ok) throw new Error("Failed");
                const data = await res.json();

                setName(data.name);
                setDescription(data.description);

                // Split prompt
                if (data.task) {
                    const { manual } = splitPrompt(data.task);
                    setTask(manual);
                } else {
                    setTask("");
                }

                // Backfill include_in_prompt for existing data
                const loadedVal = (data.validation || []).map((v: ValidationRule) => ({
                    ...v,
                    include_in_prompt: v.include_in_prompt !== undefined ? v.include_in_prompt : (v.type !== 'model')
                }));
                setValidation(loadedVal);

                setAssets(data.assets || []);

                if (data.env) {
                    setEnvVars(Object.entries(data.env).map(([key, value]) => ({ key, value: String(value) })));
                }

                if (data.github_issue) {
                    setTaskMode('github');
                    setGithubIssue(data.github_issue);
                    setGithubTaskType('issue');
                } else if (data.task) {
                    setTaskMode('prompt');
                }

                if (data.assets && data.assets.length > 0) {
                    const first = data.assets[0];
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
            } catch (e) {
                console.error(e);
                toast.error("Failed to load scenario editor");
                router.push('/scenarios');
            } finally {
                setFetching(false);
            }
        };
        fetchScenario();
    }, [id, router]);

    const addValidation = () => {
        // Validation check for empty fields
        if (newValType === 'model' && !newValTarget.trim()) {
            toast.error("AI Review instructions cannot be empty.");
            return;
        }

        const val: Partial<ValidationRule> = { type: newValType as any, include_in_prompt: newValInclude };

        if (newValType === 'command') {
            val.command = newValTarget;
            val.expected_exit_code = parseInt(newValThreshold) || 0;
        } else if (newValType === 'model') {
            val.prompt = newValTarget;
        } else if (newValType === 'manual') {
            val.target = newValTarget;
        } else {
            val.target = newValTarget || "./...";
            if (newValType === 'test') val.min_coverage = parseFloat(newValThreshold) || 0;
            if (newValType === 'lint') val.max_issues = parseInt(newValThreshold) || 0;
        }

        setValidation([...validation, val as ValidationRule]);
        setNewValTarget("");
        setNewValThreshold("");
        // Reset defaults
        setNewValInclude(true);
    };

    const removeValidation = (idx: number) => {
        setValidation(validation.filter((_, i) => i !== idx));
    };

    const toggleInclude = (idx: number) => {
        const newV = [...validation];
        newV[idx].include_in_prompt = !newV[idx].include_in_prompt;
        setValidation(newV);
    };

    const handlePromptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (ev) => {
            if (ev.target?.result) {
                // Load as manual prompt
                setTask(ev.target.result as string);
            }
        };
        reader.readAsText(file);
    };

    const handleDelete = async () => {
        if (!confirm("Are you sure you want to delete this scenario? This cannot be undone.")) return;

        setLoading(true);
        try {
            const res = await fetch(`/api/scenarios/${id}`, { method: 'DELETE' });
            if (res.ok) {
                toast.success("Scenario deleted successfully");
                router.push('/scenarios');
                router.refresh();
            } else {
                toast.error("Failed to delete scenario");
            }
        } catch (e) {
            toast.error("Error deleting scenario");
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (validation.length === 0) {
            toast.error("Scenario must have at least one validation rule.");
            return;
        }

        setLoading(true);

        const formData = new FormData();
        formData.append('name', name);
        formData.append('description', description);
        formData.append('validation', JSON.stringify(validation));

        const envMap: Record<string, string> = {};
        envVars.forEach(e => { envMap[e.key] = e.value; });
        formData.append('env', JSON.stringify(envMap));

        // Combine Manual Task + Acceptance Criteria
        if (taskMode === 'prompt' || githubTaskType === 'prompt') {
            const combinedTask = syncAcceptanceCriteria(task, validation);
            formData.append('task', combinedTask);
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

        try {
            const res = await fetch(`/api/scenarios/${id}`, {
                method: 'PUT',
                body: formData
            });

            if (res.ok) {
                toast.success("Scenario updated successfully");
                router.refresh();
            } else {
                toast.error("Failed to update scenario");
            }
        } catch (e) {
            toast.error("Error updating scenario");
        } finally {
            setLoading(false);
        }
    };

    if (fetching) return <div className="p-20 text-center text-body animate-pulse">Loading Workbench...</div>;
    if (!id) return <div className="p-20 text-center text-red-500">Missing Scenario ID</div>;

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-enter text-body">
            <PageHeader
                title="Edit Scenario"
                description={`System ID: ${id}`}
                backHref="/scenarios"
                actions={
                    <>
                        <Button variant="destructive" size="sm" onClick={handleDelete} disabled={loading}>
                            Delete Scenario
                        </Button>
                        <Button type="button" variant="default" size="lg" onClick={handleSubmit} disabled={loading}>
                            Save Changes
                        </Button>
                    </>
                }
            />

            <form onSubmit={handleSubmit} className="space-y-8">

                {/* 1. Details */}
                <Card>
                    <CardHeader>
                        <CardTitle>Scenario Details</CardTitle>
                        <CardDescription>Core identity of the scenario</CardDescription>
                    </CardHeader>
                    <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-8">
                        <div className="md:col-span-2">
                            <Input label="Display Name" value={name} onChange={(e) => setName(e.target.value)} required />
                        </div>
                        <div className="md:col-span-2">
                            <TextArea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={3} />
                        </div>

                        <div>
                            <Select
                                label="Task Source"
                                value={taskMode}
                                onChange={(e) => {
                                    const mode = e.target.value as any;
                                    setTaskMode(mode);
                                    if (mode === 'github') setAssetType('git');
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

                {/* 2. Prompt (Moved Up) */}
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
                            <div className="">
                                <Button type="button" variant="outline" onClick={addEnvVar}>Add Env</Button>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* 5. Validation Rules */}
                <Card>
                    <CardHeader>
                        <CardTitle>Validation Criteria</CardTitle>
                        <CardDescription>Automated rules for success and generated acceptance criteria</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-8">
                        {/* Rules List */}
                        <div className="space-y-3">
                            {validation.map((v, i) => (
                                <div
                                    key={i}
                                    className="flex justify-between items-center p-3 bg-card rounded border border-border group"
                                >
                                    <div className="flex gap-4 items-center overflow-hidden">
                                        <input
                                            type="checkbox"
                                            checked={!!v.include_in_prompt}
                                            onChange={(e) => toggleInclude(i)}
                                            className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-primary focus:ring-1 focus:ring-primary"
                                            title="Include in Acceptance Criteria"
                                        />
                                        <span className={`px-2 py-0.5 rounded text-mono font-bold uppercase text-[10px] whitespace-nowrap ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : v.type === 'lint' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : v.type === 'model' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' : v.type === 'manual' ? 'bg-blue-500/10 text-blue-400' : 'bg-primary/10 text-primary'}`}>{v.type}</span>
                                        <span className="text-foreground font-mono truncate text-sm">{v.type === 'command' ? v.command : v.type === 'model' ? v.prompt : v.target}</span>
                                        {v.min_coverage !== undefined && <span className="text-mono text-muted-foreground text-[10px] whitespace-nowrap">min_cov: {v.min_coverage}%</span>}
                                        {v.max_issues !== undefined && <span className="text-mono text-muted-foreground text-[10px] whitespace-nowrap">max_issues: {v.max_issues}</span>}
                                        {v.expected_exit_code !== undefined && <span className="text-mono text-muted-foreground text-[10px] whitespace-nowrap">exit: {v.expected_exit_code}</span>}
                                    </div>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); removeValidation(i); }} className="text-muted-foreground hover:text-destructive px-2">✕</button>
                                </div>
                            ))}
                            {validation.length === 0 && <p className="text-body opacity-30 italic">No validation rules defined.</p>}
                        </div>


                        <div className="p-4 bg-muted/10 border border-border rounded flex gap-4 items-start">
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
                                        { value: 'command', label: 'Shell Command' },
                                        { value: 'model', label: 'AI Review' },
                                        { value: 'manual', label: 'Manual Criteria' }
                                    ]}
                                />
                            </div>
                            <div className="flex-1">
                                {newValType === 'model' ? (
                                    <TextArea
                                        label="Review Instructions"
                                        placeholder="Prompt for an AI agent to evaluate the project. Use for checking qualitative requirements that are hard to verify with tools (e.g. 'Code must follow SOLID principles')."
                                        value={newValTarget}
                                        onChange={(e) => setNewValTarget(e.target.value)}
                                        rows={3}
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
                            {newValType !== 'model' && newValType !== 'manual' && (
                                <div className="w-[100px]">
                                    <Input
                                        label={newValType === 'test' ? 'Min Cov' : newValType === 'lint' ? 'Max Issues' : 'Exit Code'}
                                        placeholder="0"
                                        value={newValThreshold}
                                        onChange={(e) => setNewValThreshold(e.target.value)}
                                    />
                                </div>
                            )}
                            <div className="pt-8 flex items-center">
                                <label className="flex items-center gap-2 cursor-pointer" title="Add to Generated Acceptance Criteria">
                                    <input
                                        type="checkbox"
                                        checked={newValInclude}
                                        onChange={(e) => setNewValInclude(e.target.checked)}
                                        className="w-4 h-4 rounded border-zinc-700 bg-zinc-800 text-primary focus:ring-1 focus:ring-primary"
                                    />
                                    <span className="text-[10px] uppercase font-bold text-muted-foreground">Add to Prompt</span>
                                </label>
                            </div>
                            <div className="pt-8">
                                <Button type="button" variant="secondary" onClick={addValidation}>Add Rule</Button>
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
                    <Button type="submit" variant="default" size="lg" isLoading={loading}>
                        Save Changes
                    </Button>
                </div>
            </form>
        </div>
    );
}

export default function ScenarioEditorPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params);

    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ScenarioEditorContent id={id} />
        </Suspense>
    );
}