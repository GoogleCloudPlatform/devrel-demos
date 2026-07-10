/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React, { useState } from 'react';
import useSWR, { useSWRConfig } from 'swr';
import { Link } from 'react-router-dom';
import { fetcher } from '../utils/fetcher';
import type { Hackathon } from '../types/models';
import { Plus, Trash, Calendar, Settings2, Award, ClipboardCheck, Sparkles, X, Check } from 'lucide-react';

interface CriterionInput {
  name: string;
  description: string;
  weight: number;
  max_score: number;
}

const DEFAULT_CRITERIA: CriterionInput[] = [
  { name: 'Innovation & Originality', description: 'How unique and creative is the solution?', weight: 0.3, max_score: 5 },
  { name: 'Technical Execution', description: 'Code quality and technical execution completeness.', weight: 0.4, max_score: 5 },
  { name: 'User Experience (UX/UI)', description: 'Minimalist design for flow-state productivity.', weight: 0.3, max_score: 5 }
];

export default function Dashboard() {
  const { data: hackathons, error, isLoading } = useSWR<Hackathon[]>('/api/hackathons', fetcher);
  const { mutate } = useSWRConfig();

  // Modal Toggles
  const [isHackathonModalOpen, setIsHackathonModalOpen] = useState(false);
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [selectedHackathonId, setSelectedHackathonId] = useState<string | null>(null);

  // New Hackathon Form Fields
  const [hackathonTitle, setHackathonTitle] = useState('');
  const [hackathonDate, setHackathonDate] = useState('');
  const [hackathonDesc, setHackathonDescription] = useState('');
  const [hackathonGoal, setHackathonGoal] = useState('');
  const [criteria, setCriteria] = useState<CriterionInput[]>(DEFAULT_CRITERIA);
  const [bonusCriteria, setBonusCriteria] = useState<CriterionInput[]>([]);

  // New Project Form Fields
  const [projTitle, setProjTitle] = useState('');
  const [projGit, setProjGit] = useState('');
  const [projTeam, setProjTeam] = useState('');
  const [projDoc, setProjDoc] = useState('');

  // SWR Mutation Handling
  const handleCreateHackathon = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Weight sum validation
    const totalWeight = criteria.reduce((sum, c) => sum + Number(c.weight), 0);
    if (Math.abs(totalWeight - 1.0) > 0.001) {
      alert(`Criteria weights must sum to exactly 1.0 (Currently: ${totalWeight.toFixed(2)})`);
      return;
    }

    const payload = {
      title: hackathonTitle,
      date: new Date(hackathonDate).toISOString(),
      description: hackathonDesc,
      goal: hackathonGoal,
      status: 'active',
      criteria,
      bonus_criteria: bonusCriteria
    };

    try {
      const response = await fetch('/api/hackathons', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Failed to create hackathon');
      
      // Real-time local state refresh
      mutate('/api/hackathons');
      setIsHackathonModalOpen(false);
      
      // Reset form
      setHackathonTitle('');
      setHackathonDate('');
      setHackathonDescription('');
      setHackathonGoal('');
      setCriteria(DEFAULT_CRITERIA);
      setBonusCriteria([]);
    } catch (err: any) {
      alert(err.message || 'Operation failed');
    }
  };

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHackathonId) return;

    const derivedSlug = projTitle
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');

    const payload = {
      name: derivedSlug,
      title: projTitle,
      url: "",
      github_url: projGit,
      team_name: projTeam,
      document: projDoc || ""
    };

    try {
      const response = await fetch(`/api/hackathons/${selectedHackathonId}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) throw new Error('Failed to add project');
      
      setIsProjectModalOpen(false);
      setProjTitle('');
      setProjGit('');
      setProjTeam('');
      setProjDoc('');
      alert('Project successfully added to the hackathon!');
    } catch (err: any) {
      alert(err.message || 'Operation failed');
    }
  };

  // Helper arrays builders
  const addCriteriaRow = () => {
    setCriteria([...criteria, { name: '', description: '', weight: 0.1, max_score: 5 }]);
  };

  const removeCriteriaRow = (index: number) => {
    setCriteria(criteria.filter((_, i) => i !== index));
  };

  const addBonusRow = () => {
    setBonusCriteria([...bonusCriteria, { name: '', description: '', weight: 1.0, max_score: 2 }]);
  };

  const removeBonusRow = (index: number) => {
    setBonusCriteria(bonusCriteria.filter((_, i) => i !== index));
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-8">
      {/* Header Panel */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white p-6 rounded-2xl border border-slate-100 shadow-xs">
        <div>
          <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Hackathon Judge Central</h2>
          <p className="text-slate-500 mt-1">Manage hackathons, configure AI evaluators, and onboard team submissions.</p>
        </div>
        <button
          onClick={() => setIsHackathonModalOpen(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold px-5 py-3 rounded-xl hover:opacity-95 shadow-md shadow-blue-500/10 transition-all transform hover:-translate-y-0.5 cursor-pointer"
        >
          <Plus className="w-5 h-5" />
          Create Hackathon
        </button>
      </div>

      {/* Grid of Hackathons */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map(n => (
            <div key={n} className="h-64 bg-slate-100 animate-pulse rounded-2xl border border-slate-200"></div>
          ))}
        </div>
      ) : error ? (
        <div className="p-6 bg-red-50 text-red-600 rounded-xl border border-red-100">Failed to sync hackathon dashboard.</div>
      ) : !hackathons || hackathons.length === 0 ? (
        <div className="text-center p-12 bg-white rounded-2xl border border-slate-100 shadow-inner">
          <ClipboardCheck className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-slate-700">No hackathons onboarded</h3>
          <p className="text-slate-400 text-sm mt-1 mb-6">Create your first hackathon and configure AI-driven evaluation rubrics.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {hackathons.map((h) => (
            <div 
              key={h.id} 
              className="group bg-white border border-slate-100 rounded-2xl p-6 shadow-xs hover:shadow-md hover:border-blue-500/40 hover:-translate-y-1 transition-all duration-300 flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-center mb-4">
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full capitalize ${
                    h.status === 'active' ? 'bg-emerald-50 text-green-700 border border-green-100' : 'bg-slate-100 text-slate-600'
                  }`}>
                    {h.status}
                  </span>
                  <div className="flex items-center gap-1.5 text-slate-400 text-xs">
                    <Calendar className="w-3.5 h-3.5" />
                    {new Date(h.date).toLocaleDateString()}
                  </div>
                </div>

                <h3 className="text-xl font-bold text-slate-800 group-hover:text-blue-600 transition-colors mb-2">{h.title}</h3>
                <p className="text-slate-600 text-sm mb-4 line-clamp-3">{h.goal}</p>

                {/* Rubrics Preview pill */}
                <div className="flex flex-wrap gap-1.5 mb-6">
                  {h.criteria?.map((c, i) => (
                    <span key={i} className="text-[10px] font-medium bg-slate-50 text-slate-500 border border-slate-100 px-2 py-0.5 rounded-md">
                      {c.name} ({Math.round(c.weight * 100)}%)
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex gap-2 pt-4 border-t border-slate-50">
                <Link 
                  to={`/hackathons/${h.id}`}
                  className="flex-1 text-center bg-slate-50 hover:bg-slate-100 text-slate-700 font-semibold px-4 py-2.5 rounded-xl text-xs transition-colors"
                >
                  View Projects
                </Link>
                <button
                  onClick={() => {
                    setSelectedHackathonId(h.id);
                    setIsProjectModalOpen(true);
                  }}
                  className="flex items-center justify-center gap-1 bg-blue-50 hover:bg-blue-100 text-blue-600 font-semibold px-4 py-2.5 rounded-xl text-xs transition-colors cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  Add Project
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ==================== CREATE HACKATHON DIALOG (GLASSMORPHIC BACKDROP) ==================== */}
      {isHackathonModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-end">
          <div className="absolute inset-0 bg-slate-900/40 backdrop-blur-xs" onClick={() => setIsHackathonModalOpen(false)}></div>
          <div className="relative w-full max-w-2xl h-full bg-white/95 backdrop-blur-md shadow-2xl p-8 flex flex-col justify-between overflow-y-auto border-l border-slate-100">
            
            <div className="space-y-6">
              <div className="flex justify-between items-center border-b border-slate-100 pb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-6 h-6 text-indigo-600" />
                  <h3 className="text-2xl font-black text-slate-800">Add New Hackathon</h3>
                </div>
                <button onClick={() => setIsHackathonModalOpen(false)} className="text-slate-400 hover:text-slate-600 rounded-lg p-1.5 hover:bg-slate-50 transition-colors">
                  <X className="w-6 h-6" />
                </button>
              </div>

              <form onSubmit={handleCreateHackathon} className="space-y-5">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Hackathon Title</label>
                    <input 
                      type="text" 
                      required 
                      value={hackathonTitle} 
                      onChange={(e) => setHackathonTitle(e.target.value)} 
                      placeholder="e.g. Summer Productivity Jam"
                      className="w-full border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 rounded-xl px-4 py-2.5 text-slate-700 placeholder-slate-400 transition-all text-sm outline-hidden"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Event Date</label>
                    <input 
                      type="date" 
                      required 
                      value={hackathonDate} 
                      onChange={(e) => setHackathonDate(e.target.value)} 
                      className="w-full border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 rounded-xl px-4 py-2.5 text-slate-700 transition-all text-sm outline-hidden"
                    />
                  </div>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Global Goal Statement</label>
                  <input 
                    type="text" 
                    required 
                    value={hackathonGoal} 
                    onChange={(e) => setHackathonGoal(e.target.value)} 
                    placeholder="e.g. Build tools that drastically improve developer productivity."
                    className="w-full border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 rounded-xl px-4 py-2.5 text-slate-700 placeholder-slate-400 transition-all text-sm outline-hidden"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wide">Description & Details</label>
                  <textarea 
                    rows={2} 
                    required 
                    value={hackathonDesc} 
                    onChange={(e) => setHackathonDescription(e.target.value)} 
                    placeholder="Provide contextual details and rules about the competition..."
                    className="w-full border border-slate-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500/20 rounded-xl px-4 py-2.5 text-slate-700 placeholder-slate-400 transition-all text-sm outline-hidden resize-none"
                  />
                </div>

                {/* 🌟 SCORING CRITERIA LIST BUILDER */}
                <div className="space-y-3 pt-2">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-indigo-600 uppercase tracking-wide flex items-center gap-1">
                      <Settings2 className="w-4 h-4" />
                      Standard Evaluation Rubrics
                    </label>
                    <button 
                      type="button" 
                      onClick={addCriteriaRow}
                      className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-0.5 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Criterion
                    </button>
                  </div>

                  <div className="max-h-[220px] overflow-y-auto space-y-3 pr-1.5 border border-slate-100 rounded-xl p-3 bg-slate-50/50">
                    {criteria.map((item, index) => (
                      <div key={index} className="flex gap-2 items-start bg-white p-3 rounded-lg border border-slate-100 shadow-xs">
                        <div className="flex-1 space-y-2">
                          <input 
                            type="text" 
                            required 
                            placeholder="Criterion Name"
                            value={item.name}
                            onChange={(e) => {
                              const copy = [...criteria];
                              copy[index].name = e.target.value;
                              setCriteria(copy);
                            }}
                            className="w-full border-b border-slate-200 text-xs font-bold focus:border-blue-500 outline-hidden pb-0.5"
                          />
                          <input 
                            type="text" 
                            required 
                            placeholder="Scoring guidance reasoning description..."
                            value={item.description}
                            onChange={(e) => {
                              const copy = [...criteria];
                              copy[index].description = e.target.value;
                              setCriteria(copy);
                            }}
                            className="w-full text-[11px] text-slate-500 border-none outline-hidden focus:ring-0 pb-0"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-16">
                            <span className="text-[9px] text-slate-400 font-bold block mb-0.5">WEIGHT</span>
                            <input 
                              type="number" 
                              required 
                              step="0.01" 
                              min="0" 
                              max="1" 
                              value={item.weight}
                              onChange={(e) => {
                                const copy = [...criteria];
                                copy[index].weight = Number(e.target.value);
                                setCriteria(copy);
                              }}
                              className="w-full border border-slate-200 rounded-md p-1 text-xs text-center font-semibold"
                            />
                          </div>
                          <div className="w-12">
                            <span className="text-[9px] text-slate-400 font-bold block mb-0.5">MAX</span>
                            <input 
                              type="number" 
                              required 
                              min="1" 
                              value={item.max_score}
                              onChange={(e) => {
                                const copy = [...criteria];
                                copy[index].max_score = Number(e.target.value);
                                setCriteria(copy);
                              }}
                              className="w-full border border-slate-200 rounded-md p-1 text-xs text-center"
                            />
                          </div>
                          <button 
                            type="button" 
                            onClick={() => removeCriteriaRow(index)}
                            className="text-slate-300 hover:text-red-500 self-end mb-1 transition-colors"
                          >
                            <Trash className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Criteria Weights Total Indicator */}
                  <div className="flex justify-between items-center text-xs px-2">
                    <span className="font-semibold text-slate-500">Weight allocation checker:</span>
                    <span className={`font-bold flex items-center gap-1 ${
                      Math.abs(criteria.reduce((s, c) => s + c.weight, 0) - 1.0) < 0.001 
                        ? 'text-emerald-600' 
                        : 'text-amber-500'
                    }`}>
                      {Math.abs(criteria.reduce((s, c) => s + c.weight, 0) - 1.0) < 0.001 ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : null}
                      Total: {criteria.reduce((sum, c) => sum + c.weight, 0).toFixed(2)} / 1.00
                    </span>
                  </div>
                </div>

                {/* 🚀 BONUS CRITERIA BUILDER */}
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <label className="text-xs font-bold text-amber-600 uppercase tracking-wide flex items-center gap-1">
                      <Award className="w-4 h-4" />
                      Bonus Metrics (Optional)
                    </label>
                    <button 
                      type="button" 
                      onClick={addBonusRow}
                      className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline flex items-center gap-0.5 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add Bonus
                    </button>
                  </div>

                  {bonusCriteria.length > 0 && (
                    <div className="space-y-2 max-h-[140px] overflow-y-auto border border-slate-100 rounded-xl p-3 bg-slate-50/50">
                      {bonusCriteria.map((item, index) => (
                        <div key={index} className="flex gap-2 items-start bg-white p-2.5 rounded-lg border border-slate-100 shadow-xs">
                          <div className="flex-1 space-y-1">
                            <input 
                              type="text" 
                              required 
                              placeholder="Bonus Name"
                              value={item.name}
                              onChange={(e) => {
                                const copy = [...bonusCriteria];
                                copy[index].name = e.target.value;
                                setBonusCriteria(copy);
                              }}
                              className="w-full border-b border-slate-200 text-xs font-bold outline-hidden pb-0.5"
                            />
                            <input 
                              type="text" 
                              required 
                              placeholder="Reasoning details..."
                              value={item.description}
                              onChange={(e) => {
                                const copy = [...bonusCriteria];
                                copy[index].description = e.target.value;
                                setBonusCriteria(copy);
                              }}
                              className="w-full text-[10px] text-slate-500 border-none outline-hidden focus:ring-0"
                            />
                          </div>
                          <div className="flex items-center gap-2">
                            <div className="w-16">
                              <input 
                                type="number" 
                                required 
                                value={item.max_score}
                                onChange={(e) => {
                                  const copy = [...bonusCriteria];
                                  copy[index].max_score = Number(e.target.value);
                                  setBonusCriteria(copy);
                                }}
                                className="w-full border border-slate-200 rounded-md p-1 text-xs text-center"
                              />
                            </div>
                            <button type="button" onClick={() => removeBonusRow(index)} className="text-slate-300 hover:text-red-500 transition-colors">
                              <Trash className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                <div className="pt-6 border-t border-slate-100 flex justify-end gap-3">
                  <button 
                    type="button" 
                    onClick={() => setIsHackathonModalOpen(false)}
                    className="border border-slate-200 hover:bg-slate-50 text-slate-600 font-semibold px-4 py-2.5 rounded-xl text-sm transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button 
                    type="submit"
                    className="bg-gradient-to-r from-blue-600 to-indigo-600 hover:opacity-95 text-white font-semibold px-5 py-2.5 rounded-xl text-sm transition-all shadow-md shadow-blue-500/10 cursor-pointer"
                  >
                    Save & Initialize
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ==================== CREATE PROJECT DIALOG ==================== */}
      {isProjectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div 
            className="absolute inset-0 bg-slate-900 bg-opacity-60" 
            onClick={() => setIsProjectModalOpen(false)}
          ></div>
          
          <div className="relative w-full max-w-lg bg-white rounded-xl shadow-2xl border border-slate-300 overflow-hidden z-10 flex flex-col">
            {/* Header */}
            <div className="bg-slate-950 px-6 py-4 flex justify-between items-center text-white">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-blue-400" />
                <h3 className="text-lg font-bold tracking-tight">Add Team Project Submission</h3>
              </div>
              <button 
                onClick={() => setIsProjectModalOpen(false)} 
                className="text-slate-400 hover:text-white rounded-lg p-1.5 hover:bg-white/10 transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleCreateProject} className="p-6 space-y-5 bg-white">
              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Project Name <span className="text-red-500">*</span>
                </label>
                <input 
                  type="text" 
                  required 
                  value={projTitle} 
                  onChange={(e) => setProjTitle(e.target.value)} 
                  placeholder="e.g. Daybreak Planner"
                  className="w-full bg-white border border-slate-300 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 rounded-lg px-3 py-2 text-sm text-slate-950 placeholder-slate-400 font-medium transition-all"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Team Name <span className="text-red-500">*</span>
                </label>
                <input 
                  type="text" 
                  required 
                  value={projTeam} 
                  onChange={(e) => setProjTeam(e.target.value)} 
                  placeholder="e.g. Team Daybreak"
                  className="w-full bg-white border border-slate-300 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 rounded-lg px-3 py-2 text-sm text-slate-950 placeholder-slate-400 font-medium transition-all"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  GitHub URL <span className="text-red-500">*</span>
                </label>
                <input 
                  type="url" 
                  required 
                  value={projGit} 
                  onChange={(e) => setProjGit(e.target.value)} 
                  placeholder="https://github.com/your-username/your-repo"
                  className="w-full bg-white border border-slate-300 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 rounded-lg px-3 py-2 text-sm text-slate-950 placeholder-slate-400 font-medium transition-all"
                />
              </div>

              <div className="space-y-1">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Submission Document / Pitch details <span className="text-slate-400 font-normal">(Optional)</span>
                </label>
                <textarea 
                  rows={3} 
                  value={projDoc} 
                  onChange={(e) => setProjDoc(e.target.value)} 
                  placeholder="Describe your project, features, technologies used, or pitch ideas..."
                  className="w-full bg-white border border-slate-300 focus:border-blue-600 focus:ring-1 focus:ring-blue-600 rounded-lg px-3 py-2 text-sm text-slate-950 placeholder-slate-400 font-medium transition-all resize-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-slate-100 flex justify-end gap-2 bg-white">
                <button 
                  type="button" 
                  onClick={() => setIsProjectModalOpen(false)}
                  className="border border-slate-300 hover:bg-slate-50 text-slate-600 font-semibold px-4 py-2 rounded-lg text-xs"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg text-xs transition-colors shadow-sm"
                >
                  Submit Project
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
