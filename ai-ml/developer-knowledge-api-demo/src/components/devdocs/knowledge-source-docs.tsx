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
 * @file knowledge-source-docs.tsx
 * @description Renders instructions and documentation on how to use the Knowledge Sources tab.
 * Why it matters: Helps users understand how to configure API keys and add sources in the demo.
 */

import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';

import { APP_TABS, APP_TAB_LABELS } from '@/lib/constants';

// KnowledgeSourceDocs component that renders instructions and documentation on
// how to use the Knowledge Sources tab.
export function KnowledgeSourceDocs() {
  return (
    <Card className="h-full w-full overflow-hidden border-none shadow-none">
      <CardHeader className="pb-4">
        <CardTitle>{APP_TAB_LABELS[APP_TABS.SOURCES]}</CardTitle>
        <CardDescription>
          Follow these steps to configure your knowledge provider and add sources.
        </CardDescription>
      </CardHeader>
      <CardContent className="h-full p-0">
        <ScrollArea className="h-full">
          <div className="space-y-8 pb-24 px-6 pr-8 max-w-4xl">
            
            {/* Instructions */}
            <div className="space-y-6">
              <div className="space-y-2">
                <h3 className="text-xl font-semibold tracking-tight">1. Configure the API</h3>
                <p className="text-muted-foreground leading-relaxed">
                  In the sidebar on the left, locate the <strong>API Key</strong> section. Enter your API key. The settings are saved automatically when you focus away from the input field.
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold tracking-tight">2. Add knowledge sources</h3>
                <p className="text-muted-foreground leading-relaxed">
                  Click the <strong>+</strong> icon next to <strong>Sources</strong> in the sidebar to add a new knowledge source. Enter a display name and a site filter (e.g., <code>firebase.google.com/docs</code>) to limit search results to that domain.
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold tracking-tight">3. Search your knowledge sources</h3>
                <p className="text-muted-foreground leading-relaxed">
                  Go to the <strong>Search</strong> tab to query your knowledge sources.
                </p>
              </div>

              <div className="space-y-2">
                <h3 className="text-xl font-semibold tracking-tight">4. Include or exclude knowledge sources</h3>
                <p className="text-muted-foreground leading-relaxed">
                  To include or exclude a knowledge source while searching, toggle the <strong>Eye</strong> icon next to the source name in the <strong>Sources</strong> tab. A crossed out eye means the source is excluded from search results.
                </p>
              </div>
            </div>

          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
