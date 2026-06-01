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
 * @file products.ts
 * @description Defines configuration interfaces and presets for knowledge sources and providers.
 * Why it matters: Centralizes the catalog of available documentation sources for the search interface.
 */

// Interface for defining a knowledge source configuration.
export interface ProductConfig {
  id: string;
  label: string;
  description: string;
  type: 'local' | 'remote';
  siteFilter?: string; // e.g., 'firebase.google.com' or 'docs.cloud.google.com/looker'
  providerId?: string; // e.g. 'google-cloud-dkg'
  customProviderId?: string; // e.g. 'custom-provider-123', if using a custom provider
  connection?: {
    provider: string; // e.g. 'google-cloud-dkg'
    apiKey?: string;
    endpoint?: string;
  };
}

// Interface for defining a knowledge graph provider.
export interface ProviderConfig {
  id: string; // e.g. 'custom-provider-123'
  name: string; // Display name
  providerId: string; // Implementation ID, e.g. 'google-cloud-dkg'
  connection: {
    apiKey?: string;
    endpoint?: string;
  };
}

// The default selected products for the application.
export const DEFAULT_SELECTED_PRODUCTS = ['standard-dkg'];

// The default local sources for the application.
export const LOCAL_SOURCES: ProductConfig[] = [];

// The default remote presets for the application.
export const REMOTE_PRESETS: ProductConfig[] = [
  {
    id: 'standard-dkg',
    label: 'All Documentation',
    description: 'Default knowledge source',
    type: 'remote',
    providerId: 'standard-dkg'
  }
];

// Default knowledge sources for the application.
export const KNOWLEDGE_SOURCES: ProductConfig[] = [
  ...LOCAL_SOURCES,
  ...REMOTE_PRESETS
];
