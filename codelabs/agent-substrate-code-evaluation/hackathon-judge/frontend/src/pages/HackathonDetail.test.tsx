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

// src/pages/HackathonDetail.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import HackathonDetail from './HackathonDetail';
import useSWR from 'swr';

vi.mock('swr');

const mockUseSWR = useSWR as unknown as ReturnType<typeof vi.fn>;

describe('HackathonDetail Component', () => {
  it('renders loading state', () => {
    mockUseSWR.mockReturnValue({ data: undefined, error: undefined, isLoading: true });
    render(
      <MemoryRouter initialEntries={['/hackathons/1']}>
        <Routes>
          <Route path="/hackathons/:id" element={<HackathonDetail />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByText('Loading details...')).toBeInTheDocument();
  });

  it('renders projects data', async () => {
    mockUseSWR.mockImplementation((key) => {
      if (typeof key === 'string' && key.includes('/projects')) {
        if (key.endsWith('/evaluations')) {
           return { data: [], error: undefined, isLoading: false };
        }
        return {
          data: [
            { id: 'p1', title: 'AI Builder', team_name: 'Team Alpha', score: 95.5 },
          ],
          error: undefined,
          isLoading: false,
        };
      }
      if (typeof key === 'string' && key.includes('/hackathons/')) {
        return {
           data: { id: '1', title: 'Test Hackathon', date: '2026-05-11', status: 'ACTIVE', goal: 'Test Goal' },
           error: undefined,
           isLoading: false,
        };
      }
      return { data: undefined, error: undefined, isLoading: true };
    });
    
    render(
      <MemoryRouter initialEntries={['/hackathons/1']}>
        <Routes>
          <Route path="/hackathons/:id" element={<HackathonDetail />} />
        </Routes>
      </MemoryRouter>
    );
    
    await waitFor(() => {
      expect(screen.getByText('AI Builder')).toBeInTheDocument();
      expect(screen.getByText('Team: Team Alpha')).toBeInTheDocument();
      // Use regex to match the text across elements
      expect(screen.getByText(/Score:/)).toBeInTheDocument();
      expect(screen.getByText('95.50')).toBeInTheDocument();
    });
  });
});
