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

// src/pages/Dashboard.tsx
import useSWR from 'swr';
import { Link } from 'react-router-dom';
import { fetcher } from '../utils/fetcher';
import type { Hackathon } from '../types/models';

export default function Dashboard() {
  const { data: hackathons, error, isLoading } = useSWR<Hackathon[]>('/api/hackathons', fetcher);

  if (isLoading) return <div className="p-4">Loading hackathons...</div>;
  if (error) return <div className="p-4 text-red-500">Failed to load hackathons.</div>;
  if (!hackathons || hackathons.length === 0) return <div className="p-4">No hackathons found.</div>;

  return (
    <div className="p-4">
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {hackathons.map((h) => (
          <div key={h.id} className="border border-slate-200 rounded-lg p-4 bg-white hover:border-blue-600 transition-colors">
            <h3 className="text-xl font-semibold mb-2">{h.title}</h3>
            <p className="text-gray-600 mb-1">Date: {new Date(h.date).toLocaleDateString()}</p>
            <p className="text-gray-600 mb-1">Status: {h.status}</p>
            <p className="text-gray-700 mb-4 line-clamp-2">{h.goal}</p>
            <Link 
              to={`/hackathons/${h.id}`}
              className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
            >
              View Projects
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
}
