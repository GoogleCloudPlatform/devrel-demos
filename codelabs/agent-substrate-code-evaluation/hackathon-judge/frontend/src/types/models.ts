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

// frontend/src/types/models.ts
export interface Criterion {
  name: string;
  weight: number;
  description: string;
  max_score: number;
}

export interface Hackathon {
  id: string;
  title: string;
  date: string;
  description: string;
  goal: string;
  status: string;
  criteria?: Criterion[];
  bonus_criteria?: Criterion[];
}

export interface Project {
  id: string;
  name: string;
  title: string;
  url: string;
  github_url: string;
  team_name: string;
  document: string;
  date: string;
  hackathon_id: string;
  score: number;
}

export interface CriteriaScore {
  name: string;
  score: number;
  weight: number;
  reasoning?: string;
  max_score?: number;
}

export interface Evaluation {
  id: string;
  project_id: string;
  judge_id: string;
  status: string; // 'UNKNOWN' | 'RUNNING' | 'SUCCESS' | 'FAILED'
  criteria?: CriteriaScore[];
  total_score: number;
  comment?: string;
  created_at: string;
}
