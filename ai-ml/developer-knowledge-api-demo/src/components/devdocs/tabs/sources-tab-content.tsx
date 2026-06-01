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
 * @file sources-tab-content.tsx
 * @description Renders the list of knowledge sources and the API key input in the sidebar.
 * Why it matters: Allows users to manage their sources and configure the API key.
 */

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Plus, Trash2, ChevronDown, ChevronRight, Eye, EyeOff } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { useUser } from '@/contexts/user-context';
import { ProductConfig, REMOTE_PRESETS } from '@/lib/dkg/products';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { getDkgApiKey } from '@/app/actions';

import { APP_TABS, APP_TAB_LABELS } from '@/lib/constants';

interface SourcesTabContentProps {
  selectedProducts: string[];
  onProductToggle: (product: string) => void;
  knowledgeSources: ProductConfig[];
}

/**
 * SourcesTabContent component that renders the list of knowledge sources and the API key input in the sidebar.
 * 
 * @param selectedProducts Array of selected product IDs.
 * @param onProductToggle Callback function when a product is toggled.
 * @param knowledgeSources Array of all available knowledge sources.
 * @returns The JSX element for the sources tab content.
 */
export function SourcesTabContent({ selectedProducts, onProductToggle, knowledgeSources }: SourcesTabContentProps) {
  const { currentUser, updatePreferences } = useUser();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const mainProvider = currentUser?.preferences?.customProviders?.[0];
  const [apiKey, setApiKey] = useState(mainProvider?.connection?.apiKey || '');

  useEffect(() => {
    if (mainProvider) {
      setApiKey(mainProvider.connection.apiKey || '');
    }
  }, [mainProvider]);

  useEffect(() => {
    if (!apiKey) {
      getDkgApiKey().then(key => {
        if (key) setApiKey(key);
      });
    }
  }, []);

  /**
   * Updates the main provider configuration in user preferences.
   * 
   * @param updates Object containing updates to endpoint or apiKey.
   */
  const updateMainProvider = (updates: { endpoint?: string, apiKey?: string }) => {
    const currentProvs = currentUser?.preferences?.customProviders || [];
    const mainProv = currentProvs[0] || { id: 'default-provider', name: 'Default Provider', providerId: 'standard-dkg', connection: {} };

    const updatedProv = {
      ...mainProv,
      connection: {
        ...mainProv.connection,
        ...updates
      }
    };

    const updatedProvs = currentProvs.length > 0
      ? currentProvs.map((p, i) => i === 0 ? updatedProv : p)
      : [updatedProv];

    updatePreferences({ customProviders: updatedProvs });
  };

  // Collapsible states
  const [isSourcesOpen, setIsSourcesOpen] = useState(true);
  const [isProvidersOpen, setIsProvidersOpen] = useState(true);

  /**
   * Handles deleting a knowledge source.
   * 
   * @param e Mouse event to prevent propagation.
   * @param id The ID of the source to delete.
   */
  const handleDeleteSource = (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent toggling the checkbox
    if (!currentUser) return;

    const currentDkg = currentUser.preferences.dkg || { selectedProducts: [], modules: { explain: true, generate: true } };
    const newSelectedProducts = currentDkg.selectedProducts.filter(p => p !== id);

    let updates: any = {
      dkg: {
        ...currentDkg,
        selectedProducts: newSelectedProducts
      }
    };

    // Check if it's a preset
    if (REMOTE_PRESETS.some(p => p.id === id)) {
      const currentSubscribed = currentUser.preferences.subscribedPresetIds
        || REMOTE_PRESETS.map(p => p.id);
      updates.subscribedPresetIds = currentSubscribed.filter(pid => pid !== id);
    }

    // Also check if it's in custom sources and remove it
    const currentCustom = currentUser.preferences.customSources || [];
    if (currentCustom.some(s => s.id === id)) {
      updates.customSources = currentCustom.filter(s => s.id !== id);
    }

    updatePreferences(updates);
  };

  /**
   * Handles editing a knowledge source by navigating to the edit form.
   * 
   * @param e Mouse event to prevent propagation.
   * @param source The source configuration to edit.
   */
  const handleEditSource = (e: React.MouseEvent, source: ProductConfig) => {
    e.stopPropagation();
    const params = new URLSearchParams(searchParams);
    params.set('action', 'edit-source');
    params.set('sourceId', source.id);
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 pb-2">
        <h3 className="text-base font-bold">{APP_TAB_LABELS[APP_TABS.SOURCES]}</h3>
        <p className="text-sm text-muted-foreground pt-2">
          Manage your knowledge sources.
        </p>
      </div>
      <ScrollArea className="flex-1 px-4">
        <div className="space-y-6 pt-2 pb-6">

          {/* Knowledge Provider Section */}
          <Collapsible open={isProvidersOpen} onOpenChange={setIsProvidersOpen} className="space-y-2">
            <div className="flex items-center justify-between group">
              <div className="flex items-center space-x-2">
                <CollapsibleTrigger className="flex items-center hover:opacity-70 transition-opacity font-semibold">
                  {isProvidersOpen ? <ChevronDown className="h-4 w-4 mr-1" /> : <ChevronRight className="h-4 w-4 mr-1" />}
                  API Key
                </CollapsibleTrigger>
              </div>
            </div>

            <CollapsibleContent>
              <div className="space-y-3 pl-5 w-full overflow-hidden py-2">
                <div className="text-sm">
                  {apiKey ? (
                    <p className="text-green-600 dark:text-green-400 font-medium">Developer Knowledge API connected!</p>
                  ) : (
                    <p className="text-red-600 dark:text-red-400 font-medium">
                      See the README to install the Developer Knowledge API key.
                    </p>
                  )}
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>

          {/* Knowledge Sources Section */}
          <Collapsible open={isSourcesOpen} onOpenChange={setIsSourcesOpen} className="space-y-2">
            <div className="flex items-center justify-between group">
              <div className="flex items-center space-x-2">
                <CollapsibleTrigger className="flex items-center hover:opacity-70 transition-opacity font-semibold">
                  {isSourcesOpen ? <ChevronDown className="h-4 w-4 mr-1" /> : <ChevronRight className="h-4 w-4 mr-1" />}
                  Sources
                </CollapsibleTrigger>
              </div>
              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => {
                const params = new URLSearchParams(searchParams);
                params.set('action', 'add-source');
                params.delete('sourceId');
                router.push(`${pathname}?${params.toString()}`);
              }}>
                <Plus className="h-4 w-4" />
                <span className="sr-only">Add Source</span>
              </Button>
            </div>

            <CollapsibleContent>
              <div className="space-y-1 pl-2 w-full overflow-hidden">
                {/* Descriptions or Empty State */}
                {knowledgeSources.length === 0 && (
                  <p className="text-sm text-muted-foreground italic">No sources configured.</p>
                )}

                {knowledgeSources.map((source) => (
                  <div
                    key={source.id}
                    className="group flex items-center justify-between p-2 rounded-md hover:bg-sidebar-accent hover:text-sidebar-accent-foreground transition-colors w-full max-w-full"
                  >
                    <div className="flex items-start space-x-3 overflow-hidden flex-1 w-0 mr-2">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 mt-0.5 shrink-0"
                        onClick={(e) => {
                          e.stopPropagation();
                          onProductToggle(source.id);
                        }}
                      >
                        {!mounted ? (
                          source.id === 'standard-dkg' ? (
                            <Eye className="h-4 w-4 text-primary" />
                          ) : (
                            <EyeOff className="h-4 w-4 text-muted-foreground" />
                          )
                        ) : selectedProducts.includes(source.id) ? (
                          <Eye className="h-4 w-4 text-primary" />
                        ) : (
                          <EyeOff className="h-4 w-4 text-muted-foreground" />
                        )}
                      </Button>
                      <div
                        className="space-y-1 flex-1 min-w-0 cursor-pointer hover:opacity-80"
                        onClick={(e) => handleEditSource(e, source)}
                      >
                        <Label htmlFor={`prod-${source.id}`} className="font-medium text-sm truncate block cursor-pointer">
                          {source.label}
                        </Label>
                        {source.siteFilter && (
                          <div className="text-xs text-muted-foreground truncate">
                            {source.siteFilter}
                          </div>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center shrink-0">
                      <Button variant="ghost" size="icon" className="h-7 w-7" onClick={(e) => handleDeleteSource(e, source.id)}>
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </ScrollArea>
    </div>
  );
}
