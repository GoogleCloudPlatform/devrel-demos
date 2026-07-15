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
import { useParams, useNavigate } from 'react-router-dom';
import { fetcher } from '../utils/fetcher';
import type { Evaluation, Project, Hackathon } from '../types/models';

export default function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [isTriggeringAgent, setIsTriggeringAgent] = useState(false);
  const [judgeMessage, setJudgeMessage] = useState<{ text: string, type: 'success' | 'error' } | null>(null);
  
  const { data: project, error: projectError, isLoading: isProjectLoading, mutate: mutateProject } = useSWR<Project>(
    id ? `/api/projects/${id}` : null,
    fetcher
  );

  const { data: hackathon, error: hackathonError, isLoading: isHackathonLoading } = useSWR<Hackathon>(
    project?.hackathon_id ? `/api/hackathons/${project.hackathon_id}` : null,
    fetcher
  );

  const { data: evaluations, error: evalError, isLoading: isEvalLoading, mutate: mutateEvaluations } = useSWR<Evaluation[]>(
    id ? `/api/projects/${id}/evaluations` : null, 
    fetcher
  );

  const isAgentRunning = evaluations?.some(e => e.status === 'RUNNING' && e.judge_id === 'sandbox');
  const hasAgentEvaluations = evaluations?.some(e => e.judge_id === 'sandbox');
  const isRunning = isAgentRunning;

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (isRunning) {
      interval = setInterval(() => {
        mutateEvaluations();
        mutateProject();
      }, 5000);
    }
    return () => clearInterval(interval);
  }, [isRunning, mutateEvaluations, mutateProject]);

  const handleJudgeAgent = async () => {
    if (hasAgentEvaluations && !window.confirm('Agent evaluations already exist for this project. Are you sure you want to run another evaluation?')) {
      return;
    }

    setIsTriggeringAgent(true);
    setJudgeMessage(null);
    try {
      const response = await fetch(`/api/projects/${id}/judge`, { method: 'POST' });
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

  if (isProjectLoading || isEvalLoading || isHackathonLoading) return <div className="p-4">Loading details...</div>;
  if (projectError) return <div className="p-4 text-red-500">Failed to load project details.</div>;
  if (hackathonError) return <div className="p-4 text-red-500">Failed to load hackathon details.</div>;
  if (evalError) return <div className="p-4 text-red-500">Failed to load evaluations.</div>;

  return (
    <div className="p-4">
      <div className="mb-6">
        <button 
          onClick={() => navigate(-1)} 
          className="text-blue-600 hover:underline mb-4 inline-block bg-transparent border-none cursor-pointer"
        >
          &larr; Back
        </button>
        
        {project && (
          <div className="bg-white p-6 rounded-lg border border-slate-200 mb-6 shadow-sm flex justify-between items-start">
            <div className="flex-1">
              <h2 className="text-3xl font-bold mb-2">{project.title}</h2>
              <div className="text-gray-600 space-y-1">
                <p><span className="font-semibold text-gray-700">Team:</span> {project.team_name}</p>
                {project.url && (
                  <p><span className="font-semibold text-gray-700">Project URL:</span> <a href={project.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{project.url}</a></p>
                )}
                {project.github_url && (
                  <p><span className="font-semibold text-gray-700">GitHub:</span> <a href={project.github_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">{project.github_url}</a></p>
                )}
                <p className="text-xl mt-4 font-bold text-slate-800">Overall Score: <span className="text-blue-600">{typeof project.score === 'number' ? project.score.toFixed(2) : 'N/A'}</span></p>
              </div>
            </div>
            
            <div className="flex flex-col items-end gap-2">
              <div className="flex gap-2">
                <button
                  onClick={handleJudgeAgent}
                  disabled={isTriggeringAgent || isAgentRunning}
                  className={`inline-block border px-6 py-3 rounded-lg font-bold transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed ${
                    isAgentRunning ? 'border-yellow-600 bg-yellow-600 text-white' : 
                    'border-blue-600 bg-blue-600 text-white hover:bg-blue-700 hover:shadow-md active:scale-95'
                  }`}
                >
                  {isTriggeringAgent ? 'Starting...' : isAgentRunning ? 'Judging...' : hasAgentEvaluations ? 'Rerun Agent' : 'Run Agent'}
                </button>
              </div>
              {judgeMessage && (
                <p className={`text-sm font-medium ${judgeMessage.type === 'error' ? 'text-red-600' : 'text-green-600'}`}>
                  {judgeMessage.text}
                </p>
              )}
            </div>
          </div>
        )}
        
        <h2 className="text-2xl font-bold">Project Evaluations</h2>
      </div>

      {!evaluations || evaluations.length === 0 ? (
        <div>No evaluations found for this project.</div>
      ) : (
        <div className="space-y-6">
          {evaluations.map((e) => (
            <div key={e.id} className="border border-slate-200 rounded-lg p-6 bg-white shadow-sm">
              <div className="flex justify-between items-start mb-6 pb-4 border-b">
                <div>
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">Judge ID</span>
                  <p className="font-mono text-sm mt-1 bg-gray-100 px-2 py-1 rounded inline-block">{e.judge_id}</p>
                </div>
                <div>
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-bold block mb-1">Status</span>
                  <p className="font-semibold">
                    {e.status === 'RUNNING' && <span className="bg-yellow-100 text-yellow-800 text-xs px-3 py-1.5 rounded-full">RUNNING</span>}
                    {e.status === 'SUCCESS' && <span className="bg-green-100 text-green-800 text-xs px-3 py-1.5 rounded-full">SUCCESS</span>}
                    {e.status === 'FAILED' && <span className="bg-red-100 text-red-800 text-xs px-3 py-1.5 rounded-full">FAILED</span>}
                    {!['RUNNING', 'SUCCESS', 'FAILED'].includes(e.status) && <span className="bg-gray-100 text-gray-800 text-xs px-3 py-1.5 rounded-full">{e.status || 'UNKNOWN'}</span>}
                  </p>
                </div>
                <div className="text-right">
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">Total Score</span>
                  <p className="text-3xl font-black text-blue-600 mt-1">{typeof e.total_score === 'number' ? e.total_score.toFixed(2) : 'N/A'}</p>
                </div>
              </div>
              
              {e.criteria && e.criteria.length > 0 && (
                <div className="mb-6">
                  <h4 className="text-lg font-bold mb-4 text-slate-800">Criteria Breakdown</h4>
                  <div className="space-y-4">
                    {e.criteria.map((c, idx) => {
                      const criterionDef = hackathon?.criteria?.find(hc => hc.name === c.name) || hackathon?.bonus_criteria?.find(hc => hc.name === c.name);
                      const maxScore = criterionDef?.max_score ?? c.max_score;
                      const weight = criterionDef?.weight ?? c.weight;

                      return (
                        <div key={idx} className="bg-gray-50 p-4 rounded-lg border border-gray-100">
                          <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-2 pb-2 border-b border-gray-200">
                            <span className="font-bold text-slate-700 text-lg">{c.name}</span>
                            <div className="flex items-center gap-4 shrink-0">
                              <div className="text-right">
                                <span className="text-[10px] text-gray-400 uppercase font-bold block leading-none mb-1">Score</span>
                                <span className="font-black text-blue-600 text-lg">{typeof c.score === 'number' ? c.score.toFixed(2) : 'N/A'}</span>
                              </div>
                              <div className="text-right border-l border-gray-200 pl-4">
                                <span className="text-[10px] text-gray-400 uppercase font-bold block leading-none mb-1">Max</span>
                                <span className="font-bold text-slate-700">{maxScore || '-'}</span>
                              </div>
                              <div className="text-right border-l border-gray-200 pl-4">
                                <span className="text-[10px] text-gray-400 uppercase font-bold block leading-none mb-1">Weight</span>
                                <span className="font-bold text-slate-700">{weight || '-'}</span>
                              </div>
                            </div>
                          </div>
                          {c.reasoning ? (
                            <p className="text-sm text-gray-600 italic leading-relaxed">"{c.reasoning}"</p>
                          ) : (
                            <p className="text-sm text-gray-400 italic">No detailed reasoning provided.</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="bg-blue-50 p-4 rounded-lg border border-blue-100">
                <h4 className="text-sm font-bold text-blue-900 mb-2 uppercase tracking-wide">Overall Comment</h4>
                <p className="text-blue-800 leading-relaxed">
                  {e.comment || "No overall comment provided."}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

