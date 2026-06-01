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
 * @file registry.ts
 * @description Manages the registration and retrieval of different knowledge graph providers.
 * Why it matters: Allows the application to support multiple search backends and switch between them.
 */

import { KnowledgeGraphProvider } from './provider';
import { StandardDkgProvider } from './standard-dkg-provider';

// Manages the registration and retrieval of different knowledge graph providers.
class KnowledgeGraphRegistry {
  private providers: Map<string, KnowledgeGraphProvider> = new Map();

  // Initializes the registry with default providers.
  constructor() {
    // Register default providers
    this.register(new StandardDkgProvider('standard-dkg', 'Standard DKG'));
    this.register(new StandardDkgProvider('google-cloud-dkg', 'Google Cloud DKG (Legacy)'));

  }

  // Registers a new knowledge graph provider.
  register(provider: KnowledgeGraphProvider) {
    console.log(`[KnowledgeGraphRegistry] Registering provider: ${provider.id}`);
    this.providers.set(provider.id, provider);
  }

  // Returns a provider by its ID.
  get(id: string): KnowledgeGraphProvider | undefined {
    return this.providers.get(id);
  }

  // Returns all registered providers.
  getAll(): KnowledgeGraphProvider[] {
    return Array.from(this.providers.values());
  }

  // Returns the default provider.
  getDefaultProvider(): KnowledgeGraphProvider {
    const provider = this.get('google-cloud-dkg');
    if (!provider) {
      throw new Error('Default Google Cloud DKG provider not found');
    }
    return provider;
  }
}

// Creates a singleton instance of the KnowledgeGraphRegistry.
export const knowledgeGraphRegistry = new KnowledgeGraphRegistry();
