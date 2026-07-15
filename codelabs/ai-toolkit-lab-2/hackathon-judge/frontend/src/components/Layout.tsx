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

import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function Layout() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-[240px_1fr] h-screen ">
      <Sidebar />
      <div className="flex flex-col min-w-0">
        <Header />
        <main className="flex-1 bg-slate-50 overflow-y-auto">
          <div className="max-w-7xl mx-auto p-md md:p-xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
