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

// src/pages/Dashboard.test.tsx
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Dashboard from './Dashboard';
import useSWR, { useSWRConfig } from 'swr';

vi.mock('swr', () => {
  const mockMutate = vi.fn();
  return {
    default: vi.fn(),
    useSWRConfig: vi.fn(() => ({ mutate: mockMutate })),
  };
});

const mockUseSWR = useSWR as unknown as ReturnType<typeof vi.fn>;
const mockUseSWRConfig = useSWRConfig as unknown as ReturnType<typeof vi.fn>;

describe('Dashboard Component', () => {
  let mockMutate: any;

  beforeEach(() => {
    vi.restoreAllMocks();
    mockMutate = vi.fn();
    mockUseSWRConfig.mockReturnValue({ mutate: mockMutate });
    global.fetch = vi.fn() as any;
  });

  it('renders loading state (animated skeletons)', () => {
    mockUseSWR.mockReturnValue({ data: undefined, error: undefined, isLoading: true });
    const { container } = render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );
    // Loading state renders skeleton grids containing divs with 'animate-pulse'
    const skeletonGrid = container.querySelector('.animate-pulse');
    expect(skeletonGrid).toBeInTheDocument();
  });

  it('renders error state', () => {
    mockUseSWR.mockReturnValue({ data: undefined, error: new Error('Failed to load'), isLoading: false });
    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );
    expect(screen.getByText('Failed to sync hackathon dashboard.')).toBeInTheDocument();
  });

  it('renders hackathons data', async () => {
    const mockData = [
      { id: '1', title: 'Spring Hackathon', date: '2026-05-15T00:00:00Z', status: 'upcoming', goal: 'Build cool stuff' },
    ];
    mockUseSWR.mockReturnValue({ data: mockData, error: undefined, isLoading: false });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('Spring Hackathon')).toBeInTheDocument();
      expect(screen.getByText('upcoming')).toBeInTheDocument();
    });
  });

  it('handles the Delete Hackathon flow and confirms deletion', async () => {
    const mockData = [
      { id: '1', title: 'Spring Hackathon', date: '2026-05-15T00:00:00Z', status: 'upcoming', goal: 'Build cool stuff' },
    ];
    mockUseSWR.mockReturnValue({ data: mockData, error: undefined, isLoading: false });

    // Mock successful fetch for deletion
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Hackathon deleted successfully' }),
    });

    render(
      <BrowserRouter>
        <Dashboard />
      </BrowserRouter>
    );

    // Verify card is loaded
    await waitFor(() => {
      expect(screen.getByText('Spring Hackathon')).toBeInTheDocument();
    });

    // Click the "Delete" button inside the tile
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteButton);

    // Verify deletion confirmation modal appears
    expect(screen.getByText('Delete Hackathon')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to delete this hackathon?/i)).toBeInTheDocument();

    // Click the confirmation "Delete Permanently" button
    const confirmDeleteButton = screen.getByRole('button', { name: /delete permanently/i });
    fireEvent.click(confirmDeleteButton);

    // Verify fetch was called with the correct URL & Method
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith('/api/hackathons/1', {
        method: 'DELETE',
      });
      // Verify SWR mutation was triggered to refresh dashboard view
      expect(mockMutate).toHaveBeenCalledWith('/api/hackathons');
    });
  });
});
