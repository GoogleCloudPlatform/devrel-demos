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


'use client';

/**
 * @file main-layout.tsx
 * @description The main layout component that orchestrates the sidebar and content areas.
 * Why it matters: Serves as the primary container and state coordinator for the app's UI.
 */

import { useState, useMemo, useEffect, useCallback } from 'react';

import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar';

import { SourcesTabContent } from './tabs/sources-tab-content';
import { SearchTabContent } from './tabs/search-tab-content';
import { SearchResults } from './tabs/search-results';
import { AddSourceForm } from './tabs/add-source-form';

import { KnowledgeSourceDocs } from './knowledge-source-docs';
import { useDkgSearch } from '@/hooks/use-dkg-search';
import { AppSidebar } from './app-sidebar';

import { useUser } from '@/contexts/user-context';
import { DEFAULT_SELECTED_PRODUCTS, REMOTE_PRESETS } from '@/lib/dkg/products';
import { APP_TABS } from '@/lib/constants';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';

// Main layout component that orchestrates the sidebar and content areas.
export function MainLayout() {

  // Get search parameters, router, and pathname
  const searchParams = useSearchParams();

  // Get the router
  const router = useRouter();

  // Get the pathname
  const pathname = usePathname();

  // Set the active tab based on search parameters
  const activeTab = searchParams.get('tab') || APP_TABS.SEARCH;

  // Set the open filter categories
  const [openFilterCategories, setOpenFilterCategories] = useState<string[]>(['dkg-view-mode']);

  // Handles the change of an active tab
  const onTabChange = (value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set('tab', value);
    router.push(`${pathname}?${params.toString()}`);
  };

  // Handles the toggling of a filter category
  const handleToggleFilterCategory = (category: string) => {
    setOpenFilterCategories(prev =>
      prev.includes(category)
        ? prev.filter(c => c !== category)
        : [...prev, category]
    );
  };

  // Get current user and update preferences  
  const { currentUser, updatePreferences } = useUser();

  // Set selected products based on user preferences
  const [selectedProducts, setSelectedProducts] = useState<string[]>(DEFAULT_SELECTED_PRODUCTS);

  // Sync Settings from User Context
  useEffect(() => {
    if (currentUser) {
      if (currentUser.preferences.dkg) {
        const nextProducts = currentUser.preferences.dkg.selectedProducts;
        setSelectedProducts(prev => {
          const prevSorted = [...prev].sort();
          const nextSorted = [...nextProducts].sort();
          if (JSON.stringify(prevSorted) === JSON.stringify(nextSorted)) {
            return prev;
          }
          console.log('[MainLayout] Updating selectedProducts from UserContext', nextProducts);
          return nextProducts;
        });
      } else {
        updatePreferences({
          dkg: {
            selectedProducts,
            modules: { explain: true, generate: true }
          }
        });
      }
    } else {
      setSelectedProducts(DEFAULT_SELECTED_PRODUCTS);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentUser]);

  // Handles the selection of a product and updates user preferences
  const handleProductToggle = (product: string) => {
    const isSelected = selectedProducts.includes(product);
    const nextProducts = isSelected
      ? selectedProducts.filter(p => p !== product)
      : [...selectedProducts, product];

    setSelectedProducts(nextProducts);

    if (currentUser) {
      const currentDkg = currentUser.preferences.dkg || { selectedProducts: [], modules: { explain: true, generate: true } };
      updatePreferences({
        dkg: {
          ...currentDkg,
          selectedProducts: nextProducts
        }
      });
    }
  };

  // DKG State & Logic using Custom Hook
  const {
    dkgQuery, setDkgQuery,
    dkgResults,
    dkgViewMode, setDkgViewMode,
    executeSearch,
    expandedDkgNodes, handleDkgNodeExpand,
    loadingDkgNodes,
    dkgError
  } = useDkgSearch({
    selectedProducts: currentUser?.preferences?.dkg?.selectedProducts || [],
    customSources: currentUser?.preferences?.customSources
  });

  // Handles the width of the sidebar and updates user preferences
  const handleWidthChange = useCallback((width: number) => {
    if (currentUser && currentUser.preferences.sidebarWidth !== width) {
      updatePreferences({ sidebarWidth: width });
    }
  }, [currentUser, updatePreferences]);

  // Gets all knowledge sources from the user's preferences
  const allKnowledgeSources = useMemo(() => {
    const customSources = currentUser?.preferences?.customSources || [];
    const customIds = new Set(customSources.map(c => c.id));
    const subscribedIds = currentUser?.preferences?.subscribedPresetIds;

    return [
      ...REMOTE_PRESETS.filter(p => {
        const isSubscribed = !subscribedIds || subscribedIds.includes(p.id);
        return isSubscribed && !customIds.has(p.id);
      }),
      ...customSources
    ];
  }, [currentUser?.preferences?.customSources, currentUser?.preferences?.subscribedPresetIds]);

  return (
    <SidebarProvider
      defaultOpen={true}
      defaultWidth={480}
      onWidthChange={handleWidthChange}
    >
      <AppSidebar
        activeTab={activeTab}
        onTabChange={onTabChange}
        searchContent={
          <SearchTabContent
            dkgQuery={dkgQuery}
            setDkgQuery={setDkgQuery}
            executeSearch={executeSearch}
          />
        }
        sourcesContent={
          <SourcesTabContent
            selectedProducts={selectedProducts}
            onProductToggle={handleProductToggle}
            knowledgeSources={allKnowledgeSources}
          />
        }
      />
      <SidebarInset className="p-4 max-h-screen flex flex-col min-w-0">
        <div className="flex items-center gap-2 mb-4 md:hidden">
          <SidebarTrigger />
        </div>

        <div className="flex-1 min-h-0">
          {activeTab === APP_TABS.SEARCH ? (
            <SearchResults
              dkgQuery={dkgQuery}
              setDkgQuery={setDkgQuery}
              dkgResults={dkgResults}
              dkgViewMode={dkgViewMode}
              expandedDkgNodes={expandedDkgNodes}
              loadingDkgNodes={loadingDkgNodes}
              handleDkgNodeExpand={handleDkgNodeExpand}
              knowledgeSources={allKnowledgeSources}
              dkgError={dkgError}
            />
          ) : activeTab === APP_TABS.SOURCES ? (
              (() => {
                if (searchParams.get('action') === 'add-source' || searchParams.get('action') === 'edit-source') {
                  const sourceId = searchParams.get('sourceId');
                  const sourceToEdit = sourceId ? allKnowledgeSources.find(s => s.id === sourceId) : undefined;

                  return (
                    <div className="flex flex-col h-full bg-sidebar">
                      <AddSourceForm
                        sourceToEdit={sourceToEdit}
                        onCancel={() => {
                          const params = new URLSearchParams(searchParams);
                          params.delete('action');
                          params.delete('sourceId');
                          params.delete('providerId');
                          router.push(`${pathname}?${params.toString()}`);
                        }}
                      />
                    </div>
                  );
                }
                return <KnowledgeSourceDocs />;
              })()
          ) : null}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}
