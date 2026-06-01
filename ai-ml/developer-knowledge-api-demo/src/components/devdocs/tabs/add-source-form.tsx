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
 * @file add-source-form.tsx
 * @description Form component for adding or editing a custom knowledge source.
 * Why it matters: Allows users to define specific domains or paths to search across.
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useUser } from '@/contexts/user-context';
import { ProductConfig } from '@/lib/dkg/products';
import { ArrowLeft } from 'lucide-react';
import { ScrollArea } from '@/components/ui/scroll-area';

export interface AddSourceFormProps {
  sourceToEdit?: ProductConfig;
  onCancel?: () => void;
}

/**
 * AddSourceForm component for adding or editing a custom knowledge source.
 * 
 * @param sourceToEdit Optional knowledge source configuration to edit.
 * @param onCancel Callback function when the operation is cancelled.
 * @returns The JSX element for the source form.
 */
export function AddSourceForm({ sourceToEdit, onCancel }: AddSourceFormProps) {
  const { currentUser, updatePreferences } = useUser();
  const { toast } = useToast();
  const [newLabel, setNewLabel] = useState('');
  const [newSiteFilter, setNewSiteFilter] = useState('');

  // Pre-fill fields when editing
  useEffect(() => {
    if (sourceToEdit) {
      setNewLabel(sourceToEdit.label);
      setNewSiteFilter(sourceToEdit.siteFilter || '');
    } else {
      // Reset or default
      setNewLabel('');
      setNewSiteFilter('');
    }
  }, [sourceToEdit]);

  /**
   * Handles adding or updating the knowledge source in user preferences.
   */
  const handleAddSource = () => {
    if (!newLabel) return;

    const mainProvider = currentUser?.preferences?.customProviders?.[0];
    const resolvedProviderId = 'standard-dkg';
    const resolvedConnection = {
      provider: 'standard-dkg',
      apiKey: mainProvider?.connection?.apiKey,
      endpoint: mainProvider?.connection?.endpoint,
    };

    const id = sourceToEdit ? sourceToEdit.id : `custom-${Date.now()}`;
    const newSource: ProductConfig = {
      id,
      label: newLabel,
      description: 'Custom Knowledge Source',
      type: 'remote',
      siteFilter: newSiteFilter,
      providerId: resolvedProviderId,
      customProviderId: mainProvider?.id,
      connection: resolvedConnection
    };

    const currentCustom = currentUser?.preferences?.customSources || [];
    const currentDkg = currentUser?.preferences?.dkg || { selectedProducts: [], modules: { explain: true, generate: true } };

    let updatedCustom;
    if (sourceToEdit && currentCustom.some(s => s.id === id)) {
      updatedCustom = currentCustom.map(s => s.id === id ? newSource : s);
    } else {
      updatedCustom = [...currentCustom, newSource];
    }

    // Auto-select the new source if it's new
    const newSelectedProducts = currentDkg.selectedProducts.includes(id)
      ? currentDkg.selectedProducts
      : [...currentDkg.selectedProducts, id];

    updatePreferences({
      customSources: updatedCustom,
      dkg: {
        ...currentDkg,
        selectedProducts: newSelectedProducts
      }
    });

    toast({
      title: "Source Saved",
      description: "Your knowledge source has been updated.",
    });

    if (!sourceToEdit) {
      onCancel?.();
    }
  };

  return (
    <Card className="h-full border-none shadow-none flex flex-col">
      <CardHeader className="flex-none">
        <div className="flex items-center gap-2 mb-2">
          <Button variant="ghost" size="icon" onClick={onCancel} className="h-8 w-8 -ml-2">
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <CardTitle>{sourceToEdit ? 'Edit Knowledge Source' : 'Add Knowledge Source'}</CardTitle>
        </div>
        <CardDescription>
          {sourceToEdit ? 'Edit the configuration for this knowledge source.' : 'Add a remote site to your knowledge graph.'}
        </CardDescription>
      </CardHeader>

      <ScrollArea className="flex-1">
        <CardContent className="space-y-6 max-w-2xl py-2">
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="source-label">Source Name <span className="text-red-500">*</span></Label>
              <Input
                id="source-label"
                placeholder="e.g. Firebase Docs"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A display name for this source.
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="source-site">Site Filter <span className="text-red-500">*</span></Label>
              <Input
                id="source-site"
                placeholder="e.g. firebase.google.com/docs"
                value={newSiteFilter}
                onChange={(e) => setNewSiteFilter(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Domain or path to limit search results to.
              </p>
            </div>

          </div>
        </CardContent>
      </ScrollArea>

      <CardFooter className="flex-none justify-end pt-4 border-t mt-auto gap-2">
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
        <Button onClick={handleAddSource} disabled={!newLabel}>
          {sourceToEdit ? 'Save Changes' : 'Add Source'}
        </Button>
      </CardFooter>
    </Card>
  );
}
