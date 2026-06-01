// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @file app-sidebar.tsx
 * @description Renders the main sidebar with tabs for Knowledge Sources and Search.
 * Why it matters: Provides the primary navigation and control interface in the sidebar.
 */

import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
} from '@/components/ui/sidebar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { Bot, Search, Library } from 'lucide-react';
import type { ReactNode } from 'react';
import { APP_TABS, APP_TAB_LABELS } from '@/lib/constants';

interface AppSidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  searchContent: ReactNode;
  sourcesContent: ReactNode;
}

// AppSidebar component that renders the main sidebar with tabs for
// Knowledge Sources and Search.
export function AppSidebar({
  activeTab,
  onTabChange,
  searchContent,
  sourcesContent,
}: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="p-4 overflow-hidden">
        <div className="flex items-center gap-2">
          <Bot className="h-8 w-8 text-primary" />
          <h1 className="text-2xl font-bold truncate">Developer Knowledge API Demo</h1>
        </div>
      </SidebarHeader>
      <SidebarContent className="p-0">
        <Tabs
          value={activeTab}
          onValueChange={onTabChange}
          className="w-full flex flex-col flex-1 min-h-0"
        >
          <TabsList className="w-full rounded-none shrink-0">
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex-1">
                    <TabsTrigger value={APP_TABS.SOURCES} className="w-full">
                      <Library className="h-4 w-4" />
                      <span className="sr-only">{APP_TAB_LABELS[APP_TABS.SOURCES]}</span>
                    </TabsTrigger>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>{APP_TAB_LABELS[APP_TABS.SOURCES]}</p>
                </TooltipContent>
              </Tooltip>

              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex-1">
                    <TabsTrigger value={APP_TABS.SEARCH} className="w-full">
                      <Search className="h-4 w-4" />
                      <span className="sr-only">{APP_TAB_LABELS[APP_TABS.SEARCH]}</span>
                    </TabsTrigger>
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <p>{APP_TAB_LABELS[APP_TABS.SEARCH]}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </TabsList>

          <TabsContent value={APP_TABS.SOURCES} className="m-0 flex-1 min-h-0">
            {sourcesContent}
          </TabsContent>
          <TabsContent value={APP_TABS.SEARCH} className="m-0 flex-1 min-h-0">
            {searchContent}
          </TabsContent>
        </Tabs>
      </SidebarContent>
    </Sidebar>
  );
}
