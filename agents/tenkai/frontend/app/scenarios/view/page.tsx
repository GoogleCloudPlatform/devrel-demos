"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/ui/page-header";
import { Card } from "@/components/ui/card";
import { Input, TextArea, Select } from "@/components/ui/input";
import { AssetUploader } from "@/components/AssetUploader";
import { Loader2 } from "lucide-react";

function ScenarioEditorContent() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const id = searchParams.get('id');

    const [loading, setLoading] = useState(false);
    const [fetching, setFetching] = useState(true);

    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [task, setTask] = useState("");
    const [taskMode, setTaskMode] = useState<'prompt' | 'github'>('prompt');
    const [githubIssue, setGithubIssue] = useState("");
    const [githubTaskType, setGithubTaskType] = useState<'issue' | 'prompt'>('issue');
    // Assets & Links
    const [assetType, setAssetType] = useState<'none' | 'folder' | 'files' | 'git' | 'create'>('none');
    const [gitUrl, setGitUrl] = useState("");
    const [gitRef, setGitRef] = useState("");

    const [assets, setAssets] = useState<any[]>([]);

    // Validation state
    const [validation, setValidation] = useState<any[]>([]);
    const [newValType, setNewValType] = useState("test");
    const [newValTarget, setNewValTarget] = useState("");
    const [newValThreshold, setNewValThreshold] = useState("");

    // Files state for upload
    const [files, setFiles] = useState<FileList | null>(null);
    const [fileName, setFileName] = useState("");
    const [fileContent, setFileContent] = useState("");

    // Environment Variables
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
                setTask(data.task || "");
                setValidation(data.validation || []);
                setAssets(data.assets || []);

                if (data.env) {
                    setEnvVars(Object.entries(data.env).map(([key, value]) => ({ key, value: String(value) })));
                }

                // Infer modes
                if (data.github_issue) {
                    setTaskMode('github');
                    setGithubIssue(data.github_issue);
                    setGithubTaskType('issue');
                } else if (data.task) {
                    setTaskMode('prompt');
                }

                // Asset type
                if (data.assets && data.assets.length > 0) {
                    const first = data.assets[0];
                    if (first.type === 'git') {
                        setAssetType('git');
                        setGitUrl(first.source);
                        setGitRef(first.ref || "");
                    } else if (first.type === 'directory') {
                        setAssetType('folder');
                    } else if (first.type === 'file' && first.content === "") {
                        // Assuming non-inline files means uploaded assets?
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
        const val: any = { type: newValType };

        if (newValType === 'command') {
            val.command = newValTarget;
            val.expected_exit_code = parseInt(newValThreshold) || 0;
        } else if (newValType === 'model') {
            val.prompt = newValTarget; // reusing target for prompt text
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
        } else if (val.type === 'model') {
            setNewValTarget(val.prompt);
            setNewValThreshold("");
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

        // Ensure at least one validation rule is present
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

        if (taskMode === 'prompt' || githubTaskType === 'prompt') {
            formData.append('task', task);
        }
        if (taskMode === 'github' && githubTaskType === 'issue') {
            formData.append('github_issue', githubIssue);
        }

        // Asset logic
        if (assetType === 'files') {
            formData.append('asset_type', 'folder'); // Keep consistent with backend expectation or update backend
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
                body: formData // No Content-Type header; browser sets multipart boundary
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
                <Card title="Scenario Configuration">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
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
                    {(taskMode === 'prompt' || (taskMode === 'github' && githubTaskType === 'prompt')) ? (
                        <div className="space-y-4 animate-in fade-in duration-300">
                            <div className="flex justify-between items-center">
                                {/* Label logic handled by TextArea label prop usually, but we can add header here */}
                            </div>
                            <div className="relative flex justify-end mb-2">
                                <div className="relative">
                                    <input type="file" onChange={handlePromptUpload} className="absolute inset-0 opacity-0 cursor-pointer" accept=".md,.txt" />
                                    <Button type="button" variant="outline" size="sm">Upload PROMPT.md</Button>
                                </div>
                            </div>
                            <TextArea
                                label="Agent Prompt / Task"
                                value={task}
                                onChange={(e) => setTask(e.target.value)}
                                rows={12}
                                required
                                className="font-mono"
                            />
                        </div>
                    ) : (
                        <div className="space-y-4 animate-in fade-in duration-300">
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
                </Card>

                {taskMode === 'prompt' && (
                    <Card title="Workspace Assets">
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
                    </Card>
                )}

                <Card title="Environment Variables">
                    <div className="space-y-4">
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
                        <div className="flex gap-4">
                            <div className="w-1/3">
                                <Input label="Key" value={newEnvKey} onChange={(e) => setNewEnvKey(e.target.value)} placeholder="GEMINI_API_KEY" />
                            </div>
                            <div className="flex-1">
                                <Input label="Value" value={newEnvValue} onChange={(e) => setNewEnvValue(e.target.value)} placeholder="secret..." />
                            </div>
                            <div className="pt-8">
                                <Button type="button" variant="outline" onClick={addEnvVar}>Add</Button>
                            </div>
                        </div>
                    </div>
                </Card>

                <Card title="Validation Rules">
                    <div className="space-y-6">
                        <div className="space-y-3">
                            {validation.map((v, i) => (
                                <div
                                    key={i}
                                    className="flex justify-between items-center p-3 bg-card rounded border border-border cursor-pointer hover:border-primary/50 transition-colors group"
                                    onClick={() => editValidation(i)}
                                    title="Click to edit"
                                >
                                    <div className="flex gap-4 items-center">
                                        <span className={`px-2 py-0.5 rounded text-mono font-bold uppercase text-[10px] ${v.type === 'test' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : v.type === 'lint' ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400' : v.type === 'model' ? 'bg-purple-500/10 text-purple-600 dark:text-purple-400' : 'bg-primary/10 text-primary'}`}>{v.type}</span>
                                        <span className="text-foreground font-mono truncate max-w-md text-sm">{v.type === 'command' ? v.command : v.type === 'model' ? v.prompt : v.target}</span>
                                        {v.min_coverage !== undefined && <span className="text-mono text-muted-foreground text-[10px]">min_cov: {v.min_coverage}%</span>}
                                        {v.max_issues !== undefined && <span className="text-mono text-muted-foreground text-[10px]">max_issues: {v.max_issues}</span>}
                                        {v.expected_exit_code !== undefined && <span className="text-mono text-muted-foreground text-[10px]">exit: {v.expected_exit_code}</span>}
                                        {v.context !== undefined && <span className="text-mono text-muted-foreground text-[10px]">ctx: {v.context.join(', ')}</span>}
                                    </div>
                                    <button type="button" onClick={(e) => { e.stopPropagation(); removeValidation(i); }} className="text-muted-foreground hover:text-destructive px-2">✕</button>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 bg-muted/10 border border-border rounded flex gap-4 items-start">
                            <div className="w-1/4">
                                <Select
                                    label="Type"
                                    value={newValType}
                                    onChange={(e) => setNewValType(e.target.value)}
                                    options={[
                                        { value: 'test', label: 'Unit Test' },
                                        { value: 'lint', label: 'Linter' },
                                        { value: 'command', label: 'Shell Command' },
                                        { value: 'model', label: 'AI Critique' }
                                    ]}
                                />
                            </div>
                            <div className="flex-1">
                                {newValType === 'model' ? (
                                    <TextArea
                                        label="Validation Prompt"
                                        placeholder="Check if the code follows best practices..."
                                        value={newValTarget}
                                        onChange={(e) => setNewValTarget(e.target.value)}
                                        rows={3}
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
                            {newValType !== 'model' && (
                                <div className="w-1/4">
                                    <Input
                                        label={newValType === 'test' ? 'Min Coverage' : newValType === 'lint' ? 'Max Issues' : 'Exit Code'}
                                        placeholder="0"
                                        value={newValThreshold}
                                        onChange={(e) => setNewValThreshold(e.target.value)}
                                    />
                                </div>
                            )}
                            <div className="pt-8">
                                <Button type="button" variant="outline" onClick={addValidation}>Add</Button>
                            </div>
                        </div>
                    </div>
                </Card>
            </form>
        </div>
    );
}

export default function ScenarioEditorPage() {
    return (
        <Suspense fallback={<div className="flex h-screen items-center justify-center"><Loader2 className="animate-spin" /></div>}>
            <ScenarioEditorContent />
        </Suspense>
    );
}
