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
 * @file search-tab-content.tsx
 * @description Renders the search input and controls in the sidebar.
 * Why it matters: Provides the entry point for user queries in the search tab.
 */

import { useRef, useEffect } from 'react';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';

import { APP_TABS, APP_TAB_LABELS } from '@/lib/constants';

interface SearchTabContentProps {
  dkgQuery: string;
  setDkgQuery: (query: string) => void;
  executeSearch: () => void;
}

/**
 * SearchTabContent component that renders the search input and controls in the sidebar.
 * 
 * @param dkgQuery The current search query.
 * @param setDkgQuery Function to update the search query.
 * @param executeSearch Function to trigger the search.
 * @returns The JSX element for the search tab content.
 */
export function SearchTabContent({
  dkgQuery,
  setDkgQuery,
  executeSearch,
}: SearchTabContentProps) {
  const searchInputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (searchInputRef.current) {
      searchInputRef.current.style.height = 'auto';
      searchInputRef.current.style.height = `${searchInputRef.current.scrollHeight}px`;
    }
  }, [dkgQuery]);

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-2">
        <h3 className="text-base font-bold">{APP_TAB_LABELS[APP_TABS.SEARCH]}</h3>
      </div>
      <div className="flex-1 px-4 pt-2 space-y-4">
        <p className="text-sm text-muted-foreground">
          Search across all enabled knowledge sources.
        </p>
        <div className="relative">
          <Textarea
            ref={searchInputRef}
            rows={1}
            placeholder="Search concepts..."
            className="min-h-[36px] h-auto resize-none py-2 overflow-hidden"
            value={dkgQuery}
            onChange={(e) => setDkgQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                executeSearch();
              }
            }}
          />
        </div>
        <div className="flex justify-end mt-2">
          <Button onClick={executeSearch} size="sm" className="active:scale-95 transition-transform hover:bg-zinc-700 active:bg-zinc-500">
            Search
          </Button>
        </div>
      </div>
    </div>
  );
}
