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

// src/pages/ProjectDetail.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import ProjectDetail from './ProjectDetail';
import useSWR from 'swr';

vi.mock('swr');

const mockUseSWR = useSWR as unknown as ReturnType<typeof vi.fn>;

describe('ProjectDetail Component', () => {
  it('renders loading state', () => {
    mockUseSWR.mockReturnValue({ data: undefined, error: undefined, isLoading: true });
    render(
      <MemoryRouter initialEntries={['/projects/p1']}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectDetail />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Loading details...')).toBeInTheDocument();
  });

  it('renders evaluations data and project details', async () => {
    const mockEvaluations = [
      { 
        id: 'e1', 
        judge_id: 'j1', 
        total_score: 85, 
        comment: 'Good work', 
        criteria: [
          // Providing an incorrect max_score/weight here to ensure the component overrides it with the hackathon's values.
          { name: 'Technical depth', score: 9, max_score: 5, weight: 1.0, reasoning: 'Impressive use of tech' }
        ] 
      },
    ];
    const mockProject = {
      id: 'p1', title: 'Awesome App', team_name: 'Team Alpha', url: 'https://example.com', hackathon_id: 'h1'
    };
    const mockHackathon = {
      id: 'h1',
      title: 'Test Hackathon',
      criteria: [
        { name: 'Technical depth', max_score: 10, weight: 1.5, description: '' }
      ],
      bonus_criteria: []
    };

    mockUseSWR.mockImplementation((url) => {
      if (url?.includes('/evaluations')) {
        return { data: mockEvaluations, error: undefined, isLoading: false };
      }
      if (url?.includes('/projects/')) {
        return { data: mockProject, error: undefined, isLoading: false };
      }
      if (url?.includes('/hackathons/')) {
        return { data: mockHackathon, error: undefined, isLoading: false };
      }
      return { data: undefined, error: undefined, isLoading: true };
    });
    
    render(
      <MemoryRouter initialEntries={['/projects/p1']}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectDetail />} />
        </Routes>
      </MemoryRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByText('Awesome App')).toBeInTheDocument();
      expect(screen.getByText('Team Alpha')).toBeInTheDocument();
      expect(screen.getByText(/Total Score/)).toBeInTheDocument();
      expect(screen.getByText('Good work')).toBeInTheDocument();
      
      // Check criteria details
      expect(screen.getByText('Technical depth')).toBeInTheDocument();
      expect(screen.getByText('Score')).toBeInTheDocument();
      expect(screen.getByText('Max')).toBeInTheDocument();
      expect(screen.getByText('Weight')).toBeInTheDocument();
      expect(screen.getByText('9.00')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('1.5')).toBeInTheDocument();
      expect(screen.getByText(/"Impressive use of tech"/)).toBeInTheDocument();
      expect(screen.getByText('85.00')).toBeInTheDocument();
    });
  });
});
