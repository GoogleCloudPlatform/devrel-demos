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
 * @file provider.ts
 * @description Defines interfaces for Knowledge Graph providers, search options, and results.
 * Why it matters: Establishes the contract for implementing new search backends.
 */

import { DkgNode } from '../dkg/schema';
import { ProductConfig } from '../dkg/products';

// Configuration for a knowledge graph provider.
export interface ProviderConfig {
  id: string;
  name: string;
  providerId: string;
  connection: {
    apiKey?: string;
    endpoint?: string;
  };
  description?: string;
}

// Options for searching the knowledge graph.
export interface SearchOptions {
  allowedSites?: string[];
  limit?: number;
  config?: ProductConfig;
  items?: any[];
}

// The result of a knowledge graph search.
export interface SearchResult {
  nodes: DkgNode[];
  metadata?: Record<string, any>;
}

// Interface for a knowledge graph provider.
export interface KnowledgeGraphProvider {
  id: string;
  name: string;
  search(query: string, options?: SearchOptions): Promise<SearchResult>;
}
