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

import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Sidebar from './Sidebar';
import { expect, test } from 'vitest';

test('renders brand and navigation links with correct hrefs', () => {
  render(
    <BrowserRouter>
      <Sidebar />
    </BrowserRouter>
  );
  
  expect(screen.getByText(/Hackathon Judge/i)).toBeInTheDocument();
  
  const homeLink = screen.getByRole('link', { name: /home/i });
  const dashboardLink = screen.getByRole('link', { name: /dashboard/i });
  const aboutLink = screen.getByRole('link', { name: /about/i });

  expect(homeLink).toHaveAttribute('href', '/');
  expect(dashboardLink).toHaveAttribute('href', '/dashboard');
  expect(aboutLink).toHaveAttribute('href', '/about');
});
