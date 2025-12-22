'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// --- Types ---
interface Alternative {
    name: string;
    description?: string;
}

interface Scenario {
    name: string;
    description?: string;
}

interface TemplateConfig {
    name: string;
    description?: string;
    repetitions?: number;
    max_concurrent?: number;
    timeout?: string;
    alternatives: Alternative[];
    scenarios: Scenario[];
}

interface TemplateDetails {
    name: string;
    suggestedName: string;
    config: TemplateConfig;
}

// --- Component ---
export default function ExperimentForm() {
    const router = useRouter();

    // --- State ---
    const [loading, setLoading] = useState(false);
    const [templates, setTemplates] = useState<{ id: string, name: string }[]>([]);
    const [selectedTemplateName, setSelectedTemplateName] = useState<string>('');
    const [templateDetails, setTemplateDetails] = useState<TemplateDetails | null>(null);

    // Form Overrides
    const [runName, setRunName] = useState('');
    const [reps, setReps] = useState(1);
    const [concurrent, setConcurrent] = useState(1);

    // Scopes
    const [selectedAlts, setSelectedAlts] = useState<string[]>([]);
    const [selectedScens, setSelectedScens] = useState<string[]>([]);
    const [controlAlt, setControlAlt] = useState<string>('');

    // --- Effects ---

    // 1. Load Template List
    useEffect(() => {
        async function fetchTemplates() {
            try {
                const res = await fetch('/api/templates');
                const data = await res.json();
                if (Array.isArray(data)) {
                    setTemplates(data);
                    if (data.length > 0 && !selectedTemplateName) {
                        setSelectedTemplateName(data[0].id);
                    }
                }
            } catch (e) {
                console.error("Failed to list templates", e);
            }
        }
        fetchTemplates();
    }, []);

    // 2. Load Template Details (When selection changes)
    useEffect(() => {
        if (!selectedTemplateName) return;

        async function fetchDetails() {
            setLoading(true);
            try {
                const res = await fetch(`/api/templates/${selectedTemplateName}`);
                const data = await res.json();

                if (data && !data.error) {
                    setTemplateDetails(data);

                    // Pre-fill Defaults
                    setRunName(data.suggestedName || '');
                    setReps(data.config.repetitions || 1);
                    setConcurrent(data.config.max_concurrent || 1);

                    // Default to ALL selected
                    const allAlts = data.config.alternatives?.map((a: Alternative) => a.name) || [];
                    setSelectedAlts(allAlts);
                    // Set control to the first alternative by default (or explicit if available)
                    if (allAlts.length > 0) setControlAlt(allAlts[0]);

                    setSelectedScens(data.config.scenarios?.map((s: Scenario) => s.name) || []);
                }
            } catch (e) {
                console.error("Failed to load template details", e);
            } finally {
                setLoading(false);
            }
        }
        fetchDetails();
    }, [selectedTemplateName]);

    // --- Handlers ---

    const handleToggleAlt = (name: string) => {
        setSelectedAlts(prev => {
            const next = prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name];
            // If we deselected the current control, reset it
            if (controlAlt === name && !next.includes(name)) {
                setControlAlt('');
            }
            // If we selected the first one and no control is set, select it
            if (next.length === 1 && !controlAlt) {
                setControlAlt(next[0]);
            }
            return next;
        });
    };

    const handleToggleScen = (name: string) => {
        setSelectedScens(prev => prev.includes(name) ? prev.filter(n => n !== name) : [...prev, name]);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (selectedAlts.length === 0 || selectedScens.length === 0) {
            alert("Experiments must have at least one Alternative and one Scenario.");
            return;
        }

        setLoading(true);
        try {
            const payload = {
                name: runName,
                template: selectedTemplateName,
                reps: reps,
                concurrent: concurrent,
                alternatives: selectedAlts,
                scenarios: selectedScens,
                control: controlAlt
            };

            const res = await fetch('/api/experiments/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (res.ok) {
                router.push('/?started=true');
            } else {
                throw new Error("API responded with error");
            }
        } catch (err) {
            console.error(err);
            alert("Failed to launch experiment. See console.");
        } finally {
            setLoading(false);
        }
    };

    const totalJobs = selectedAlts.length * selectedScens.length * reps;

    return (
        <div className="w-full max-w-[1920px] mx-auto p-6 lg:p-10 animate-in fade-in duration-500">
            <header className="flex justify-between items-start mb-10">
                <div>
                    <button
                        onClick={() => router.push('/')}
                        className="text-sm font-bold text-blue-500 uppercase tracking-widest hover:text-blue-400 transition-colors mb-2 block"
                    >
                        ← Dashboard
                    </button>
                    <h1 className="text-3xl font-bold tracking-tight text-white">New Experiment</h1>
                    <p className="text-zinc-500 mt-1 font-medium">Configure a new run from a certified template.</p>
                </div>
                <div>
                    <button
                        onClick={handleSubmit}
                        disabled={loading || !templateDetails || totalJobs === 0}
                        className="bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-800 disabled:text-zinc-500 text-white text-base font-bold uppercase tracking-wider px-8 py-4 rounded-lg shadow-lg hover:shadow-blue-500/20 transition-all flex items-center gap-3"
                    >
                        {loading ? 'Starting...' : `Launch Run (${totalJobs})`} 🚀
                    </button>
                </div>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">

                {/* COLUMN 1: CONFIGURATION (Fixed Width) */}
                <div className="lg:col-span-3 space-y-6">
                    <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 overflow-hidden">
                        <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest mb-6">Run Configuration</h3>

                        <div className="space-y-6">
                            {/* Template Select */}
                            <div>
                                <label className="block text-base font-bold text-zinc-300 mb-2">Template</label>
                                <div className="relative">
                                    <select
                                        className="w-full bg-black border border-zinc-800 rounded-lg px-4 py-3 text-white appearance-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all font-medium"
                                        value={selectedTemplateName}
                                        onChange={(e) => setSelectedTemplateName(e.target.value)}
                                        disabled={loading}
                                    >
                                        <option value="" disabled>Select a template...</option>
                                        {templates.map(t => (
                                            <option key={t.id} value={t.id}>{t.name}</option>
                                        ))}
                                    </select>
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 text-xs">▼</div>
                                </div>
                                {templateDetails?.config.description && (
                                    <p className="text-sm text-zinc-500 mt-3 leading-relaxed border-l-2 border-zinc-800 pl-3">
                                        {templateDetails.config.description}
                                    </p>
                                )}
                            </div>

                            {/* Run Name */}
                            <div>
                                <label className="block text-base font-bold text-zinc-300 mb-2">Run Name (ID)</label>
                                <input
                                    type="text"
                                    className="w-full bg-black border border-zinc-800 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all font-mono text-base"
                                    value={runName}
                                    onChange={(e) => setRunName(e.target.value)}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-bold text-zinc-500 uppercase mb-2">Repetitions</label>
                                    <input
                                        type="number"
                                        min="1" max="100"
                                        className="w-full bg-black border border-zinc-800 rounded-lg px-3 py-3 text-white focus:border-blue-500 outline-none font-mono text-base text-center"
                                        value={reps}
                                        onChange={(e) => setReps(parseInt(e.target.value) || 1)}
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-bold text-zinc-500 uppercase mb-2">Concurrency</label>
                                    <input
                                        type="number"
                                        min="1" max="50"
                                        className="w-full bg-black border border-zinc-800 rounded-lg px-3 py-3 text-white focus:border-blue-500 outline-none font-mono text-base text-center"
                                        value={concurrent}
                                        onChange={(e) => setConcurrent(parseInt(e.target.value) || 1)}
                                    />
                                </div>
                            </div>

                            {/* Stats */}
                            <div className="pt-6 border-t border-zinc-800 grid grid-cols-2 gap-4">
                                <div>
                                    <div className="text-xs font-black text-zinc-600 uppercase">Timeout</div>
                                    <div className="text-base font-mono text-zinc-400 mt-1">{templateDetails?.config.timeout || "5m"}</div>
                                </div>
                                <div>
                                    <div className="text-xs font-black text-zinc-600 uppercase">Est. Jobs</div>
                                    <div className="text-base font-mono text-emerald-500 mt-1">{totalJobs}</div>
                                </div>
                            </div>

                            {/* Control Selection */}
                            {selectedAlts.length > 0 && (
                                <div className="pt-6 border-t border-zinc-800">
                                    <label className="block text-sm font-bold text-zinc-500 uppercase mb-2">Control Algorithm</label>
                                    <div className="relative">
                                        <select
                                            className="w-full bg-black border border-zinc-800 rounded-lg px-4 py-3 text-white appearance-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all font-medium"
                                            value={controlAlt}
                                            onChange={(e) => setControlAlt(e.target.value)}
                                            disabled={loading}
                                        >
                                            <option value="" disabled>Select control...</option>
                                            {selectedAlts.map(alt => (
                                                <option key={alt} value={alt}>{alt}</option>
                                            ))}
                                        </select>
                                        <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-zinc-600 text-xs">▼</div>
                                    </div>
                                    <p className="text-xs text-zinc-600 mt-2">Baseline for statistical comparison.</p>
                                </div>
                            )}
                        </div>
                    </section>
                </div>

                {/* COLUMN 2: ALTERNATIVES (Flexible) */}
                <div className="lg:col-span-5 space-y-6">
                    <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 h-full min-h-[500px]">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest">Alternatives</h3>
                            <button
                                onClick={() => templateDetails && setSelectedAlts(templateDetails.config.alternatives.map(a => a.name))}
                                className="text-xs font-bold text-blue-500 hover:text-blue-400 uppercase tracking-wider"
                            >
                                Select All
                            </button>
                        </div>

                        {!templateDetails ? <LoadingState /> : (
                            <div className="space-y-3">
                                {templateDetails.config.alternatives.map(alt => {
                                    const isSelected = selectedAlts.includes(alt.name);
                                    return (
                                        <div
                                            key={alt.name}
                                            onClick={() => handleToggleAlt(alt.name)}
                                            className={`group p-4 rounded-lg border cursor-pointer transition-all duration-200 relative overflow-hidden ${isSelected
                                                ? 'bg-blue-600/10 border-blue-500/50'
                                                : 'bg-black/20 border-zinc-800 hover:bg-zinc-800 hover:border-zinc-700'
                                                }`}
                                        >
                                            <div className="flex items-start gap-4 z-10 relative">
                                                <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${isSelected ? 'bg-blue-600 border-blue-600 shadow-md shadow-blue-900/20' : 'border-zinc-700 bg-zinc-900'
                                                    }`}>
                                                    {isSelected && <span className="text-white text-xs font-black">✓</span>}
                                                </div>
                                                <div>
                                                    <h4 className={`text-base font-bold ${isSelected ? 'text-blue-400' : 'text-zinc-300 group-hover:text-white'}`}>
                                                        {alt.name}
                                                        {alt.name === controlAlt && <span className="ml-2 text-[10px] bg-blue-500 text-white px-2 py-0.5 rounded-full uppercase tracking-widest">Control</span>}
                                                    </h4>
                                                    {alt.description && (
                                                        <p className="text-sm text-zinc-500 mt-1.5 leading-relaxed">
                                                            {alt.description}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            {isSelected && <div className="absolute inset-0 bg-blue-600/5 pointer-events-none" />}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </section>
                </div>

                {/* COLUMN 3: SCENARIOS (Flexible) */}
                <div className="lg:col-span-4 space-y-6">
                    <section className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 h-full min-h-[500px]">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-sm font-black text-zinc-500 uppercase tracking-widest">Scenarios</h3>
                            <button
                                onClick={() => templateDetails && setSelectedScens(templateDetails.config.scenarios.map(s => s.name))}
                                className="text-xs font-bold text-emerald-500 hover:text-emerald-400 uppercase tracking-wider"
                            >
                                Select All
                            </button>
                        </div>

                        {!templateDetails ? <LoadingState /> : (
                            <div className="space-y-3">
                                {templateDetails.config.scenarios.map(scen => {
                                    const isSelected = selectedScens.includes(scen.name);
                                    return (
                                        <div
                                            key={scen.name}
                                            onClick={() => handleToggleScen(scen.name)}
                                            className={`group p-4 rounded-lg border cursor-pointer transition-all duration-200 relative overflow-hidden ${isSelected
                                                ? 'bg-emerald-600/10 border-emerald-500/50'
                                                : 'bg-black/20 border-zinc-800 hover:bg-zinc-800 hover:border-zinc-700'
                                                }`}
                                        >
                                            <div className="flex items-start gap-4 z-10 relative">
                                                <div className={`w-5 h-5 rounded border flex items-center justify-center shrink-0 mt-0.5 transition-colors ${isSelected ? 'bg-emerald-600 border-emerald-600 shadow-md shadow-emerald-900/20' : 'border-zinc-700 bg-zinc-900'
                                                    }`}>
                                                    {isSelected && <span className="text-white text-xs font-black">✓</span>}
                                                </div>
                                                <div>
                                                    <h4 className={`text-base font-bold ${isSelected ? 'text-emerald-400' : 'text-zinc-300 group-hover:text-white'}`}>
                                                        {scen.name}
                                                    </h4>
                                                    {scen.description && (
                                                        <p className="text-sm text-zinc-500 mt-1.5 leading-relaxed">
                                                            {scen.description}
                                                        </p>
                                                    )}
                                                </div>
                                            </div>
                                            {isSelected && <div className="absolute inset-0 bg-emerald-600/5 pointer-events-none" />}
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </section>
                </div>

            </div>
        </div>
    );
}

function LoadingState() {
    return (
        <div className="h-64 flex flex-col items-center justify-center text-zinc-700 animate-pulse">
            <div className="w-8 h-8 rounded-full border-2 border-zinc-800 border-t-zinc-600 animate-spin mb-4"></div>
            <p className="text-xs uppercase font-bold tracking-widest">Loading...</p>
        </div>
    );
}

