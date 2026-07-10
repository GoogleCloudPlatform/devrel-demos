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

import { useState, useEffect } from 'react';
import useSWR from 'swr';
import { useParams, Link } from 'react-router-dom';
import { fetcher } from '../utils/fetcher';
import type { Project, Evaluation, Hackathon } from '../types/models';
import { Plus, X } from 'lucide-react';

function ProjectCard({ project, evaluations, mutateEvaluations }: { project: Project, evaluations?: Evaluation[], mutateEvaluations: () => void }) {
  const [isTriggeringAgent, setIsTriggeringAgent] = useState(false);
  const [judgeMessage, setJudgeMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null);

  const isAgentRunning = evaluations?.some(e => e.status === 'RUNNING' && e.judge_id === 'sandbox');
  const hasAgentEvaluations = evaluations?.some(e => e.judge_id === 'sandbox');
  const isRunning = isAgentRunning;

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isRunning) {
      interval = setInterval(() => {
        mutateEvaluations();
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [isRunning, mutateEvaluations]);

  const handleJudgeAgent = async () => {
    if (hasAgentEvaluations && !window.confirm('Agent evaluations already exist for this project. Are you sure you want to run another evaluation?')) {
      return;
    }

    setIsTriggeringAgent(true);
    setJudgeMessage(null);
    try {
      const response = await fetch(`/api/projects/${project.id}/judge`, { method: 'POST' });
      if (!response.ok) throw new Error('Failed to start judging');
      setJudgeMessage({ text: 'Agent judging task started!', type: 'success' });
      setTimeout(() => mutateEvaluations(), 1000);
    } catch {
      setJudgeMessage({ text: 'Error starting judging', type: 'error' });
    } finally {
      setIsTriggeringAgent(false);
      setTimeout(() => setJudgeMessage(null), 3000);
    }
  };

  return (
    <div className="border border-slate-200 rounded-lg p-4 bg-white hover:border-blue-600 transition-colors shadow-sm">
      <h3 className="text-xl font-semibold mb-2">{project.title}</h3>
      <p className="text-gray-600 mb-1">Team: {project.team_name}</p>
      <p className="text-gray-600 mb-4 font-medium text-lg">Score: <span className="text-blue-600 font-bold">{typeof project.score === 'number' ? project.score.toFixed(2) : 'N/A'}</span></p>
      
      <div className="flex flex-col gap-2">
        <div className="flex gap-2">
          <Link 
            to={`/projects/${project.id}`}
            className="flex-1 text-center border border-blue-600 text-blue-600 px-3 py-2 rounded hover:bg-blue-50 transition-colors font-medium text-sm"
          >
            View
          </Link>
          <button
            onClick={handleJudgeAgent}
            disabled={isTriggeringAgent || isAgentRunning}
            className={`flex-1 border px-3 py-2 rounded transition-all disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm ${
              isAgentRunning ? 'border-yellow-600 bg-yellow-600 text-white' : 
              'border-blue-600 bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isTriggeringAgent ? '...' : isAgentRunning ? 'Running...' : hasAgentEvaluations ? 'Rerun Agent' : 'Run Agent'}
          </button>
        </div>
        {judgeMessage && (
          <p className={`text-xs mt-1 ${judgeMessage.type === 'error' ? 'text-red-600' : 'text-green-600'}`}>
            {judgeMessage.text}
          </p>
        )}
      </div>
    </div>
  );
}

export default function HackathonDetail() {
  const { id } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<'projects' | 'criteria'>('projects');
  
  const { data: hackathon, error: hackathonError, isLoading: isHackathonLoading } = useSWR<Hackathon>(id ? `/api/hackathons/${id}` : null, fetcher);
  const { data: projects, error: projectsError, isLoading: isProjectsLoading, mutate: mutateProjects } = useSWR<Project[]>(id ? `/api/hackathons/${id}/projects` : null, fetcher);

  // New Project Form Fields
  const [isProjectModalOpen, setIsProjectModalOpen] = useState(false);
  const [projTitle, setProjTitle] = useState('');
  const [projGit, setProjGit] = useState('');
  const [projTeam, setProjTeam] = useState('');
  const [projDoc, setProjDoc] = useState('');

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id) return;

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
      const response = await fetch(`/api/hackathons/${id}/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to add project');
      }
      
      setIsProjectModalOpen(false);
      setProjTitle('');
      setProjGit('');
      setProjTeam('');
      setProjDoc('');
      
      await mutateProjects();
      alert('Project successfully added to the hackathon!');
    } catch (err: any) {
      alert(err.message || 'Operation failed');
    }
  };

  const { data: evaluationsData, mutate: mutateEvaluations } = useSWR<Evaluation[][]>(
    projects && projects.length > 0 ? `hackathon-${id}-evaluations` : null,
    () => Promise.all(projects!.map(p => fetcher(`/api/projects/${p.id}/evaluations`).catch(() => [])))
  );

  const getEvaluationsForProject = (projectId: string) => {
    if (!projects || !evaluationsData) return [];
    const index = projects.findIndex(p => p.id === projectId);
    return evaluationsData[index] || [];
  };

  if (isHackathonLoading || isProjectsLoading) return <div className="p-4">Loading details...</div>;
  if (hackathonError) return <div className="p-4 text-red-500">Failed to load hackathon details.</div>;
  if (projectsError) return <div className="p-4 text-red-500">Failed to load projects.</div>;

  
  return (
    <div className="p-4">
      <div className="mb-6">
        <Link to="/dashboard" className="text-blue-600 hover:underline mb-4 inline-block">&larr; Back to Dashboard</Link>
        {hackathon && (
          <div className="bg-white p-6 rounded-lg border border-slate-200 mb-6 shadow-sm">
            <div className="flex justify-between items-start">
              <div>
                <h2 className="text-3xl font-bold mb-2">{hackathon.title}</h2>
                <p className="text-gray-500 mb-4">{new Date(hackathon.date).toLocaleDateString()} &middot; Status: <span className="font-medium text-slate-700 uppercase text-sm tracking-wide">{hackathon.status}</span></p>
              </div>
            </div>
            <div className="prose max-w-none text-gray-700">
              <p className="font-semibold text-lg mb-2">Goal:</p>
              <p>{hackathon.goal}</p>
            </div>
          </div>
        )}
      </div>

      <div className="mb-6 border-b border-gray-200 flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <nav className="-mb-px flex space-x-8 overflow-x-auto">
          <button
            onClick={() => setActiveTab('projects')}
            className={`${
              activeTab === 'projects'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Projects
          </button>
          <button
            onClick={() => setActiveTab('criteria')}
            className={`${
              activeTab === 'criteria'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
          >
            Judging Criteria
          </button>
        </nav>
        {activeTab === 'projects' && (
          <button
            onClick={() => setIsProjectModalOpen(true)}
            className="flex items-center justify-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded-lg text-xs transition-colors shadow-sm cursor-pointer mb-2 shrink-0 self-start sm:self-auto"
          >
            <Plus className="w-4 h-4" />
            Add Project
          </button>
        )}
      </div>

      {activeTab === 'projects' && (
        <>
          {!projects || projects.length === 0 ? (
            <div>No projects found for this hackathon.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((p) => (
                <ProjectCard 
                  key={p.id} 
                  project={p} 
                  evaluations={getEvaluationsForProject(p.id)}
                  mutateEvaluations={mutateEvaluations}
                />
              ))}
            </div>
          )}
        </>
      )}

      {activeTab === 'criteria' && hackathon && (
        <div className="space-y-8">
          <section>
            <h3 className="text-xl font-bold mb-4">Standard Criteria</h3>
            {(!hackathon.criteria || hackathon.criteria.length === 0) ? (
              <p className="text-gray-500">No standard criteria defined.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {hackathon.criteria.map((c, idx) => (
                  <div key={idx} className="bg-white p-4 border rounded-lg shadow-sm">
                    <div className="flex flex-col sm:flex-row justify-between sm:items-start gap-2 mb-2">
                      <h4 className="font-bold text-lg text-slate-800">{c.name}</h4>
                      <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full font-medium shrink-0 self-start sm:self-auto">Weight: {c.weight} &middot; Max: {c.max_score}</span>
                    </div>
                    <p className="text-gray-600 text-sm">{c.description}</p>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <h3 className="text-xl font-bold mb-4 text-purple-700">Bonus Criteria</h3>
            {(!hackathon.bonus_criteria || hackathon.bonus_criteria.length === 0) ? (
              <p className="text-gray-500">No bonus criteria defined.</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {hackathon.bonus_criteria.map((c, idx) => (
                  <div key={idx} className="bg-purple-50 p-4 border border-purple-100 rounded-lg shadow-sm">
                    <div className="flex flex-col sm:flex-row justify-between sm:items-start gap-2 mb-2">
                      <h4 className="font-bold text-lg text-purple-900">{c.name}</h4>
                      <span className="bg-purple-200 text-purple-900 text-xs px-2 py-1 rounded-full font-medium shrink-0 self-start sm:self-auto">Weight: {c.weight} &middot; Max: {c.max_score}</span>
                    </div>
                    <p className="text-purple-700 text-sm">{c.description}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
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
