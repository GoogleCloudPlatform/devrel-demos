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

import { NavLink } from 'react-router-dom';
import { Home, LayoutDashboard, Info } from 'lucide-react';
import UnicornMascot from './UnicornMascot';

const navItems = [
  { name: 'Home', path: '/', icon: Home },
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'About', path: '/about', icon: Info },
];

export default function Sidebar() {
  return (
    <aside className="hidden md:flex bg-primary text-white border-r border-white/10 shadow-sm z-10 flex-col w-[240px]">
      <div className="p-lg border-b border-white/10">
        <UnicornMascot />
      </div>
      <nav className="flex-1 p-md">
        <ul className="flex flex-col gap-sm">
          {navItems.map((item) => (
            <li key={item.path}>
              <NavLink
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center gap-md px-md py-sm rounded transition-colors text-sm font-semibold tracking-wide ${
                    isActive ? 'bg-white/20 text-white' : 'text-white/70 hover:bg-white/10 hover:text-white'
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                {item.name}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </aside>
  );
}
