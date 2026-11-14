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

import { render, screen, fireEvent } from '@testing-library/react';
import Header from './Header';
import { expect, test } from 'vitest';
import { BrowserRouter } from 'react-router-dom';

test('renders search, default status, and default user profile', () => {
  render(
    <BrowserRouter>
      <Header />
    </BrowserRouter>
  );
  
  expect(screen.getByPlaceholderText(/Search projects/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/Search/i)).toBeInTheDocument();
  expect(screen.getByText(/ACTIVE JUDGE/i)).toBeInTheDocument();
  expect(screen.getByText(/Judge User/i)).toBeInTheDocument();
  expect(screen.getByText(/JD/i)).toBeInTheDocument();
});

test('opens notification dropdown on click', () => {
  render(
    <BrowserRouter>
      <Header />
    </BrowserRouter>
  );

  const notificationBtn = screen.getByLabelText(/Notifications/i);
  fireEvent.click(notificationBtn);

  expect(screen.getByText(/No new notifications/i)).toBeInTheDocument();
  expect(screen.getByText(/View all/i)).toBeInTheDocument();
});

test('renders with custom user and status', () => {
  const customUser = {
    name: "Jane Doe",
    initials: "JD",
    role: "Admin"
  };
  const customStatus = "Idle";

  render(
    <BrowserRouter>
      <Header user={customUser} status={customStatus} />
    </BrowserRouter>
  );

  expect(screen.getByText(/IDLE/i)).toBeInTheDocument();
  expect(screen.getByText(/Jane Doe/i)).toBeInTheDocument();
  expect(screen.getByText(/Admin/i)).toBeInTheDocument();
});
