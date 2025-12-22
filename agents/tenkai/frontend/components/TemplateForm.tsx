'use client';

import { useState, useEffect } from 'react';
import yaml from 'js-yaml';
import { useRouter } from 'next/navigation';

interface Alternative {
    name: string;
    description: string;
    command: string;
    args: string[];
    settings_path?: string;
    system_prompt_file?: string;
}

interface Scenario {
    name: string;
    description: string;
}

interface TemplateConfig {
    name: string;
    description: string;
    repetitions: number;
    max_concurrent: number;
    timeout: string;
    alternatives: Alternative[];
    scenarios: Scenario[];
}

interface TemplateFormProps {
    initialContent?: string;
    onSubmit: (content: string) => Promise<void>;
    isCreating?: boolean;
    name?: string;
}

export default function TemplateForm({ initialContent, onSubmit, isCreating = false, name }: TemplateFormProps) {
    const [activeTab, setActiveTab] = useState<'visual' | 'yaml'>('visual');
    const [yamlContent, setYamlContent] = useState(initialContent || '');
    const [parsedConfig, setParsedConfig] = useState<TemplateConfig | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);

    // Sync YAML to Visual
    useEffect(() => {
        try {
            if (yamlContent.trim()) {
                const parsed = yaml.load(yamlContent) as TemplateConfig;
                // Ensure arrays exist
                if (!parsed.alternatives) parsed.alternatives = [];
                if (!parsed.scenarios) parsed.scenarios = [];
                setParsedConfig(parsed);
                setError(null);
            }
        } catch (e: any) {
            console.error("YAML Parse Error", e);
            // Don't set error purely on typing (too noisy), but maybe store it
        }
    }, []);

    // Switch Handlers
    const handleSwitchToYaml = () => {
        if (parsedConfig) {
            try {
                const newYaml = yaml.dump(parsedConfig);
                setYamlContent(newYaml);
            } catch (e) {
                console.error("Failed to dump YAML", e);
            }
        }
        setActiveTab('yaml');
    };

    const handleSwitchToVisual = () => {
        try {
            const parsed = yaml.load(yamlContent) as TemplateConfig;
            if (!parsed.alternatives) parsed.alternatives = [];
            if (!parsed.scenarios) parsed.scenarios = [];
            setParsedConfig(parsed);
            setError(null);
            setActiveTab('visual');
        } catch (e: any) {
            setError(`Invalid YAML: ${e.message}`);
            return; // Stay on YAML tab
        }
    };

    const handleSubmit = async () => {
        setSaving(true);
        setError(null);
        try {
            let contentToSave = yamlContent;
            if (activeTab === 'visual' && parsedConfig) {
                contentToSave = yaml.dump(parsedConfig);
            } else if (activeTab === 'yaml') {
                // Validate before saving
                yaml.load(yamlContent); // Throws if invalid
                contentToSave = yamlContent;
            }

            await onSubmit(contentToSave);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setSaving(false);
        }
    };

    // -- Field Updaters (Visual Mode) --
    const updateField = (field: keyof TemplateConfig, value: any) => {
        if (!parsedConfig) return;
        setParsedConfig({ ...parsedConfig, [field]: value });
    };

    const addAlternative = () => {
        if (!parsedConfig) return;
        setParsedConfig({
            ...parsedConfig,
            alternatives: [
                ...parsedConfig.alternatives,
                { name: 'new_alt', description: '', command: 'gemini', args: [] }
            ]
        });
    };

    const updateAlternative = (idx: number, field: keyof Alternative, value: any) => {
        if (!parsedConfig) return;
        const newAlts = [...parsedConfig.alternatives];
        newAlts[idx] = { ...newAlts[idx], [field]: value };
        setParsedConfig({ ...parsedConfig, alternatives: newAlts });
    };

    const removeAlternative = (idx: number) => {
        if (!parsedConfig) return;
        const newAlts = parsedConfig.alternatives.filter((_, i) => i !== idx);
        setParsedConfig({ ...parsedConfig, alternatives: newAlts });
    };

    const addScenario = () => {
        if (!parsedConfig) return;
        setParsedConfig({
            ...parsedConfig,
            scenarios: [
                ...parsedConfig.scenarios,
                { name: 'new_scenario', description: '' }
            ]
        });
    };

    const updateScenario = (idx: number, field: keyof Scenario, value: any) => {
        if (!parsedConfig) return;
        const newScens = [...parsedConfig.scenarios];
        newScens[idx] = { ...newScens[idx], [field]: value };
        setParsedConfig({ ...parsedConfig, scenarios: newScens });
    };

    const removeScenario = (idx: number) => {
        if (!parsedConfig) return;
        const newScens = parsedConfig.scenarios.filter((_, i) => i !== idx);
        setParsedConfig({ ...parsedConfig, scenarios: newScens });
    };

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center bg-zinc-900/50 p-2 rounded-lg border border-white/5">
                <div className="flex gap-2">
                    <button
                        onClick={handleSwitchToVisual}
                        className={`px-4 py-2 rounded-md text-sm font-bold uppercase tracking-widest transition-all ${activeTab === 'visual' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-500 hover:text-white'}`}
                    >
                        Visual Editor
                    </button>
                    <button
                        onClick={handleSwitchToYaml}
                        className={`px-4 py-2 rounded-md text-sm font-bold uppercase tracking-widest transition-all ${activeTab === 'yaml' ? 'bg-blue-600 text-white shadow-lg' : 'text-zinc-500 hover:text-white'}`}
                    >
                        YAML Source
                    </button>
                </div>
                <button
                    onClick={handleSubmit}
                    disabled={saving}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 px-6 rounded-lg shadow-lg shadow-emerald-500/20 transition-all border border-emerald-400/20 uppercase text-sm tracking-widest disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {saving ? 'Saving...' : 'Save Changes'}
                </button>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl text-sm font-bold">
                    Error: {error}
                </div>
            )}

            {activeTab === 'yaml' ? (
                <div className="h-[70vh] rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-[#1e1e1e]">
                    <textarea
                        value={yamlContent}
                        onChange={(e) => setYamlContent(e.target.value)}
                        className="w-full h-full bg-transparent text-gray-300 font-mono text-base p-6 focus:outline-none resize-none"
                        spellCheck="false"
                    />
                </div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-in fade-in duration-300">
                    {/* General Settings */}
                    <div className="space-y-6">
                        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                            <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest mb-6">General Settings</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-bold text-zinc-400 mb-1">Name</label>
                                    <input
                                        type="text"
                                        className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white font-mono text-sm focus:border-blue-500 outline-none"
                                        value={parsedConfig?.name || ''}
                                        onChange={(e) => updateField('name', e.target.value)}
                                        placeholder="Internal experiment name (YAML)"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-zinc-400 mb-1">Description</label>
                                    <textarea
                                        className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white text-sm focus:border-blue-500 outline-none h-24 resize-none"
                                        value={parsedConfig?.description || ''}
                                        onChange={(e) => updateField('description', e.target.value)}
                                    />
                                </div>
                                <div className="grid grid-cols-3 gap-4">
                                    <div>
                                        <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Reps</label>
                                        <input
                                            type="number"
                                            className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white font-mono text-sm focus:border-blue-500 outline-none"
                                            value={parsedConfig?.repetitions || 1}
                                            onChange={(e) => updateField('repetitions', parseInt(e.target.value) || 1)}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Concurrent</label>
                                        <input
                                            type="number"
                                            className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white font-mono text-sm focus:border-blue-500 outline-none"
                                            value={parsedConfig?.max_concurrent || 1}
                                            onChange={(e) => updateField('max_concurrent', parseInt(e.target.value) || 1)}
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs font-bold text-zinc-500 uppercase mb-1">Timeout</label>
                                        <input
                                            type="text"
                                            className="w-full bg-black border border-zinc-800 rounded px-3 py-2 text-white font-mono text-sm focus:border-blue-500 outline-none"
                                            value={parsedConfig?.timeout || '5m'}
                                            onChange={(e) => updateField('timeout', e.target.value)}
                                        />
                                    </div>
                                </div>
                            </div>
                        </section>

                        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest">Scenarios</h3>
                                <button onClick={addScenario} className="text-xs text-blue-500 font-bold uppercase hover:text-blue-400">+ Add</button>
                            </div>
                            <div className="space-y-4">
                                {parsedConfig?.scenarios.map((scen, idx) => (
                                    <div key={idx} className="bg-black/40 border border-zinc-800 p-4 rounded-lg relative group">
                                        <button
                                            onClick={() => removeScenario(idx)}
                                            className="absolute top-2 right-2 text-zinc-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            ✕
                                        </button>
                                        <div className="space-y-3">
                                            <input
                                                type="text"
                                                placeholder="Scenario Name"
                                                className="w-full bg-transparent border-0 border-b border-zinc-800 focus:border-blue-500 text-white font-bold text-sm px-0 py-1"
                                                value={scen.name}
                                                onChange={(e) => updateScenario(idx, 'name', e.target.value)}
                                            />
                                            <input
                                                type="text"
                                                placeholder="Description"
                                                className="w-full bg-transparent border-0 text-zinc-400 text-xs px-0 py-1"
                                                value={scen.description}
                                                onChange={(e) => updateScenario(idx, 'description', e.target.value)}
                                            />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>

                    {/* Alternatives */}
                    <div className="space-y-6">
                        <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 h-full">
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest">Alternatives</h3>
                                <button onClick={addAlternative} className="text-xs text-blue-500 font-bold uppercase hover:text-blue-400">+ Add</button>
                            </div>
                            <div className="space-y-4">
                                {parsedConfig?.alternatives.map((alt, idx) => (
                                    <div key={idx} className="bg-black/40 border border-zinc-800 p-4 rounded-lg relative group">
                                        <button
                                            onClick={() => removeAlternative(idx)}
                                            className="absolute top-2 right-2 text-zinc-600 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            ✕
                                        </button>
                                        <div className="grid gap-3">
                                            <div className="grid grid-cols-2 gap-3">
                                                <input
                                                    type="text"
                                                    placeholder="Name"
                                                    className="w-full bg-transparent border-0 border-b border-zinc-800 focus:border-blue-500 text-white font-bold text-sm px-0 py-1"
                                                    value={alt.name}
                                                    onChange={(e) => updateAlternative(idx, 'name', e.target.value)}
                                                />
                                                <input
                                                    type="text"
                                                    placeholder="Command (e.g. gemini)"
                                                    className="w-full bg-transparent border-0 border-b border-zinc-800 focus:border-blue-500 text-zinc-300 font-mono text-xs px-0 py-1 text-right"
                                                    value={alt.command}
                                                    onChange={(e) => updateAlternative(idx, 'command', e.target.value)}
                                                />
                                            </div>
                                            <textarea
                                                placeholder="Description"
                                                className="w-full bg-transparent border-0 text-zinc-400 text-xs px-0 py-1 h-16 resize-none"
                                                value={alt.description}
                                                onChange={(e) => updateAlternative(idx, 'description', e.target.value)}
                                            />
                                            <div>
                                                <label className="text-[10px] uppercase text-zinc-600 font-bold block mb-1">Args</label>
                                                <input
                                                    type="text"
                                                    placeholder='--model "gemini-1.5-pro" --yolo'
                                                    className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-zinc-300 font-mono text-xs"
                                                    value={Array.isArray(alt.args) ? alt.args.join(' ') : alt.args}
                                                    onChange={(e) => updateAlternative(idx, 'args', e.target.value.split(' '))}
                                                />
                                            </div>
                                            <div className="grid grid-cols-2 gap-3">
                                                <div>
                                                    <label className="text-[10px] uppercase text-zinc-600 font-bold block mb-1">System Prompt</label>
                                                    <input
                                                        type="text"
                                                        placeholder="path/to/prompt.md"
                                                        className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-zinc-300 font-mono text-xs"
                                                        value={alt.system_prompt_file || ''}
                                                        onChange={(e) => updateAlternative(idx, 'system_prompt_file', e.target.value)}
                                                    />
                                                </div>
                                                <div>
                                                    <label className="text-[10px] uppercase text-zinc-600 font-bold block mb-1">Settings Path</label>
                                                    <input
                                                        type="text"
                                                        placeholder="settings.json"
                                                        className="w-full bg-zinc-900 border border-zinc-800 rounded px-2 py-1 text-zinc-300 font-mono text-xs"
                                                        value={alt.settings_path || ''}
                                                        onChange={(e) => updateAlternative(idx, 'settings_path', e.target.value)}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </section>
                    </div>
                </div>
            )}
        </div>
    );
}
