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
 * @file standard-dkg-provider.ts
 * @description Implements the KnowledgeGraphProvider interface for the Developer Knowledge API.
 * Why it matters: This is the main search provider that fetches results from the remote API.
 */

import { KnowledgeGraphProvider, SearchOptions, SearchResult } from './provider';
import { DkgNode } from '../dkg/schema';
import { parseSectionsFromMarkdown } from '../dkg/markdown-utils';

const BASE_URL = 'https://developerknowledge.googleapis.com/v1alpha';
const API_KEY = undefined; // Disabled looking at environment variables

// Interface for a raw result from the Developer Knowledge API.
interface DkgApiResult {
  title?: string;
  name?: string;
  id?: string;
  url?: string;
  uri?: string;
  snippet?: string;
  summary?: string;
  content?: string;
  body?: string;
  parent?: string; // e.g. "documents/firebase.google.com/docs/..."
}

// Implements the KnowledgeGraphProvider interface for the Developer Knowledge API.
export class StandardDkgProvider implements KnowledgeGraphProvider {
  id: string;
  name: string;

  // Initializes the provider with an ID and name.
  constructor(id: string = 'standard-dkg', name: string = 'Standard DKG') {
    this.id = id;
    this.name = name;
  }

  // Searches the Developer Knowledge API for documents matching the query.
  async search(query: string, options?: SearchOptions): Promise<SearchResult> {
    if (!API_KEY) {
      if (this.id === 'google-cloud-dkg') {
        console.warn('DKG_API_KEY not set, skipping Google Cloud DKG search.');
        return { nodes: [] };
      }
    }

    try {
      let finalQuery = query;
      const allowedSites = options?.allowedSites || [];

      if (allowedSites.length > 0) {
        const siteFilter = allowedSites.map(site => `site:${site}`).join(' OR ');
        finalQuery = `${query} (${siteFilter})`;
      }

      const limit = options?.limit || 20;

      // Use config for API Key if available
      const config = options?.config;
      const apiKey = config?.connection?.apiKey || API_KEY;
      const endpoint = BASE_URL; // Hardcoded endpoint

      if (!apiKey) {
        console.warn(`[${this.name}] API Key not set and no custom key provided, skipping search.`);
        return { nodes: [] };
      }

      // Allow endpoint to end with / or without
      const baseUrl = endpoint.endsWith('/') ? endpoint.slice(0, -1) : endpoint;
      const url = `${baseUrl}/documents:searchDocumentChunks?key=${apiKey}&query=${encodeURIComponent(finalQuery)}&pageSize=${limit}`;

      // Force no-store to avoid Next.js caching in dev
      const response = await fetch(url, { cache: 'no-store' });

      if (!response.ok) {
        console.error(`[${this.name}] API failed: ${response.status} ${response.statusText}`);
        return { nodes: [] };
      }

      const json = await response.json();
      let results: DkgApiResult[] = json.results || json.documents || [];

      console.log(`[${this.name}] Raw Search Results: ${results.length}`);

      // Strict client-side filtering to fix leaky API behavior
      if (allowedSites.length > 0) {
        results = results.filter(doc => {
          const url = doc.url || doc.uri || doc.parent || '';
          return allowedSites.some(site => url.includes(site));
        });
        console.log(`[${this.name}] Filtered Search Results: ${results.length}`);
      }

      console.log(`[${this.name}] Mapping ${results.length} results to nodes...`);
      const nodes = results.map(doc => this.mapResultToNode(doc));
      console.log(`[${this.name}] Mapped to ${nodes.length} nodes.`);
      return { nodes };
    } catch (error) {
      console.error(`Error searching ${this.name}:`, error);
      return { nodes: [] };
    }
  }

  // Maps a raw API result document to a structured DkgNode.
  private mapResultToNode(doc: DkgApiResult): DkgNode {
    let originalUrl = doc.url || doc.uri || '';
    if (!originalUrl && doc.parent) {
      originalUrl = doc.parent.replace(/^documents\//, '');
    }
    let title = doc.title || doc.name || 'Untitled';

    const rawContent = doc.content || doc.body || '';
    const content = rawContent.length > 500000 ? rawContent.slice(0, 500000) : rawContent;
    const h1Match = content.match(/^#\s+(.+)$/m);

    if (h1Match) {
      title = h1Match[1].trim();
    } else {
      try {
        let clean = originalUrl.replace(/^https?:\/\//, '');
        const parts = clean.split('/').filter(p => p.length > 0);
        if (parts.length > 0) {
          const last = parts[parts.length - 1];
          let readable = last.replace(/[-_]/g, ' ');
          readable = readable.replace(/\b\w/g, c => c.toUpperCase());
          if (readable.length > 1) {
            title = readable;
          }
        }
      } catch (e) {
        // keep original
      }

      // Heuristic for Firebase REST API docs
      if (title === 'Database' && originalUrl.includes('firebase.google.com') && originalUrl.includes('/rest/')) {
        title = 'Firebase Database REST API';
      }
    }

    // Smart Description Extraction
    let description = doc.snippet || doc.summary || title || 'Remote result';
    try {
      // Clean headers
      let cleanContent = content.replace(/^(\s*#+\s+.*(\r?\n|$))+/g, '').trim();
      const paragraphMatch = cleanContent.match(/^([^#\r\n]+)/);
      if (paragraphMatch) {
        const candidate = paragraphMatch[1].trim();
        if (candidate.length > 20) {
          description = candidate.length > 250 ? candidate.substring(0, 247) + '...' : candidate;
        }
      }
    } catch (e) {
      // ignore
    }

    // Generate a deterministic ID based on the URL so we can try to recover it later
    const safeId = originalUrl
      ? `remote-${Buffer.from(originalUrl).toString('base64').replace(/=/g, '')}`
      : `remote-${title.replace(/[^a-z0-9]+/g, '-')}`;

    return {
      id: safeId,
      type: 'concept',
      title: title,
      description: description,
      content: content,
      sourcePath: '',
      metadata: {
        source: 'dkg-api',
        originalUrl: originalUrl,
        provider: 'standard-dkg' // Generic identifier for this format
      },
      sections: parseSectionsFromMarkdown(content)
    };
  }
}
