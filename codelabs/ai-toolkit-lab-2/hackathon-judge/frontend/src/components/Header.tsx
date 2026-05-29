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

import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Settings, Search, ChevronDown } from 'lucide-react';

interface User {
  name: string;
  initials: string;
  role: string;
}

interface HeaderProps {
  user?: User;
  status?: string;
}

const defaultUser: User = {
  name: "Judge User",
  initials: "JD",
  role: "Technical Track"
};

const defaultStatus = "Active Judge";

export default function Header({ user = defaultUser, status = defaultStatus }: HeaderProps) {
  const [showNotifications, setShowNotifications] = useState(false);
  const notificationRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (notificationRef.current && !notificationRef.current.contains(event.target as Node)) {
        setShowNotifications(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header className="h-[64px] border-b border-slate-200 bg-white flex items-center justify-between px-lg z-20">
      {/* Left: Search */}
      <div className="flex items-center gap-sm bg-slate-50 border border-slate-300 px-md py-xs rounded-md w-[320px] group focus-within:ring-2 focus-within:ring-secondary/20 focus-within:border-secondary transition-all">
        <Search className="w-4 h-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="Search projects, teams, or hackathons..." 
          aria-label="Search"
          className="bg-transparent border-none outline-none text-sm w-full text-slate-900 placeholder:text-slate-500"
        />
        <kbd className="hidden sm:inline-flex items-center gap-1 px-1.5 font-sans text-[10px] font-medium text-slate-400 bg-white border border-slate-300 rounded shadow-xs">
          ⌘K
        </kbd>
      </div>

      {/* Right: Utilities & User */}
      <div className="flex items-center gap-xl">
        {/* Status Badge */}
        <div className="flex items-center gap-xs bg-secondary-container/10 px-sm py-[2px] rounded-full border border-secondary-container/20">
          <div className="w-2 h-2 rounded-full bg-secondary"></div>
          <span className="text-[10px] font-bold text-secondary tracking-widest uppercase">
            {status}
          </span>
        </div>

        {/* Icons */}
        <div className="flex items-center gap-md text-slate-600 relative">
          <div className="relative" ref={notificationRef}>
            <button 
              aria-label="Notifications" 
              onClick={() => setShowNotifications(!showNotifications)}
              className={`p-1.5 rounded-md hover:bg-slate-100 hover:text-secondary transition-all cursor-pointer ${showNotifications ? 'bg-slate-100 text-secondary' : ''}`}
            >
              <Bell className="w-5 h-5" />
            </button>
            
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-lg shadow-xl py-2 z-50">
                <div className="px-4 py-2 border-b border-slate-100">
                  <h3 className="font-semibold text-slate-900">Notifications</h3>
                </div>
                <div className="px-4 py-8 text-center">
                  <p className="text-slate-500 text-sm">No new notifications</p>
                </div>
                <div className="px-4 py-2 border-t border-slate-100 text-center">
                  <button className="text-xs text-secondary font-medium hover:underline">View all</button>
                </div>
              </div>
            )}
          </div>
          
          <Link 
            to="/settings"
            aria-label="Settings" 
            className="p-1.5 rounded-md hover:bg-slate-100 hover:text-secondary transition-all cursor-pointer"
          >
            <Settings className="w-5 h-5" />
          </Link>
        </div>

        {/* User Profile */}
        <div className="flex items-center gap-md border-l border-slate-200 pl-xl cursor-pointer group">
          <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold ring-2 ring-transparent group-hover:ring-secondary/20 transition-all">
            {user.initials}
          </div>
          <div className="hidden md:flex flex-col">
            <span className="text-sm font-semibold text-slate-900 leading-tight">{user.name}</span>
            <span className="text-[11px] text-slate-500 leading-tight">{user.role}</span>
          </div>
          <ChevronDown className="w-3 h-3 text-slate-400 group-hover:text-slate-600 transition-colors" />
        </div>
      </div>
    </header>
  );
}
