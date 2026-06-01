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
 * @file use-dkg-search.ts
 * @description Custom hook to manage Developer Knowledge Graph (DKG) search state and API calls.
 * Why it matters: Encapsulates the search logic and result handling for the search interface.
 */

import { useState, useEffect } from 'react';

// Interface for the useDkgSearch hook properties.
interface UseDkgSearchProps {
  selectedProducts: string[];
  customSources?: any[]; // ProductConfig[]
}

// Custom hook to manage Developer Knowledge Graph (DKG) search state and API calls.
export function useDkgSearch({ selectedProducts, customSources = [] }: UseDkgSearchProps) {
  const [dkgQuery, setDkgQuery] = useState('');
  const [dkgResults, setDkgResults] = useState<any[]>([]);
  const [activeDkgNode, setActiveDkgNode] = useState<any | null>(null);
  const [expandedDkgNodes, setExpandedDkgNodes] = useState<Record<string, any>>({});
  const [loadingDkgNodes, setLoadingDkgNodes] = useState<Record<string, boolean>>({});
  const [dkgViewMode, setDkgViewMode] = useState<'topics' | 'sections'>('sections');
  const [dkgError, setDkgError] = useState<string | null>(null);

  // Execute search query against the DKG API
  const executeSearch = async () => {
    if (dkgQuery.length > 2) {
      try {
        const productsParam = selectedProducts.join(',');
        const relevantCustom = customSources.filter(s => selectedProducts.includes(s.id));
        const customParam = relevantCustom.length > 0 ? JSON.stringify(relevantCustom) : '';

        const res = await fetch(`/api/dkg/v1/search?q=${encodeURIComponent(dkgQuery)}&products=${encodeURIComponent(productsParam)}&custom_sources=${encodeURIComponent(customParam)}`);
        if (res.ok) {
          const data = await res.json();
          setDkgResults(data.results || []);
          setDkgError(null);
        } else {
          let errorMessage = 'Failed to fetch results';
          try {
            const data = await res.json();
            errorMessage = data.error || errorMessage;
          } catch (e) {
            // JSON parsing failed
          }
          setDkgError(errorMessage);
          setDkgResults([]);
        }
      } catch (e) {
        console.error(e);
      }
    } else {
      setDkgResults([]);
    }
  };

  // Set the active DKG node
  const handleSelectDkgNode = async (node: any) => {
    setActiveDkgNode(node);
  };

  // Fetch details for nodes that are being expanded and not already cached
  const handleDkgNodeExpand = async (ids: string[]) => {
    const missingIds = ids.filter(id => !expandedDkgNodes[id] && !loadingDkgNodes[id]);

    if (missingIds.length === 0) return;

    setLoadingDkgNodes(prev => ({ ...prev, ...Object.fromEntries(missingIds.map(id => [id, true])) }));

    missingIds.forEach(async (id) => {
      try {
        const res = await fetch(`/api/dkg/v1/node/${id}`);
        if (res.ok) {
          const data = await res.json();
          setExpandedDkgNodes(prev => ({ ...prev, [id]: data }));
        }
      } catch (e) {
        console.error(e);
      } finally {
        setLoadingDkgNodes(prev => {
          const next = { ...prev };
          delete next[id];
          return next;
        });
      }
    });
  };

  return {
    dkgQuery,
    setDkgQuery,
    dkgResults,
    setDkgResults,
    dkgError,
    activeDkgNode,
    setActiveDkgNode,
    expandedDkgNodes,
    setExpandedDkgNodes,
    loadingDkgNodes,
    setLoadingDkgNodes,
    dkgViewMode,
    setDkgViewMode,
    executeSearch,
    handleSelectDkgNode,
    handleDkgNodeExpand,
  };
}
