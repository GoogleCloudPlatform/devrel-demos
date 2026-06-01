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
 * @file dkg-api.ts
 * @description Provides high-level functions to search the Developer Knowledge Graph.
 * Why it matters: Serves as the main entry point for search operations in the application.
 */

import { DkgNode } from './schema';
import { knowledgeGraphRegistry } from '../knowledge-graph/registry';
import { StandardDkgProvider } from '../knowledge-graph/standard-dkg-provider';

// Interface for a documentation item.
export interface DkgApiResult {
  title?: string;
  name?: string;
  id?: string;
  url?: string;
  uri?: string;
  snippet?: string;
  summary?: string;
  content?: string;
  body?: string;
}

// Searches the Developer Knowledge Graph using a specific provider.
export async function searchKnowledgeGraph(providerId: string, query: string, options: any = {}): Promise<DkgNode[]> {
  let provider = knowledgeGraphRegistry.get(providerId);

  if (!provider) {
    console.warn(`Provider ${providerId} not found in registry. Attempting to instantiate on the fly.`);
    // If we have config, we can try to instantiate a standard provider on the fly
    if (options.config) {
      provider = new StandardDkgProvider(providerId, options.config.label || providerId);
    } else {
      console.warn(`No config provided for missing provider ${providerId}, aborting search.`);
      return [];
    }
  }

  const result = await provider.search(query, options);
  return result.nodes;
}
