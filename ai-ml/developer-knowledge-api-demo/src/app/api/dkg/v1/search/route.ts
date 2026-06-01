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
 * @file route.ts (search)
 * @description API route handler for searching the Developer Knowledge Graph.
 * Why it matters: Handles incoming search requests and interacts with the DKG API provider.
 */

import { NextRequest, NextResponse } from 'next/server';
import { searchKnowledgeGraph } from '@/lib/dkg/dkg-api';
import { getDkgApiKey } from '@/app/actions';
import { KNOWLEDGE_SOURCES, DEFAULT_SELECTED_PRODUCTS, ProductConfig } from '@/lib/dkg/products';

/**
 * Handles GET requests to search the Developer Knowledge Graph.
 * Supports filtering by products and custom sources specified in query parameters.
 * 
 * @param request The incoming Next.js request object.
 * @returns A JSON response with the search results or an error message.
 */
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.get('q')?.toLowerCase();

  if (!query) {
    return NextResponse.json({ error: 'Missing query parameter "q"' }, { status: 400 });
  }

  try {
    const productsParam = searchParams.get('products');
    // Default to both if not specified, or respect empty list if explicitly provided as empty string
    const products = productsParam !== null ? productsParam.split(',').filter(p => p) : DEFAULT_SELECTED_PRODUCTS;
    // Load custom sources from query param
    const customSourcesParam = searchParams.get('custom_sources');
    let customSources: ProductConfig[] = [];
    if (customSourcesParam) {
      try {
        customSources = JSON.parse(customSourcesParam);
      } catch (e) {
        console.error('Failed to parse custom_sources', e);
      }
    }

    const apiKey = await getDkgApiKey();
    if (!apiKey) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }
    const remoteSearchPromises: Promise<any[]>[] = [];

    for (const prodId of products) {
      const config = customSources.find(c => c.id === prodId) || KNOWLEDGE_SOURCES.find(k => k.id === prodId);

      if (config?.type === 'remote') {
        const providerId = config.providerId || 'google-cloud-dkg';
        const allowedSites = config.siteFilter ? [config.siteFilter] : [];

        const baseConfig = config;
        const configWithAuth = { ...baseConfig, connection: { ...baseConfig?.connection, apiKey } };

        remoteSearchPromises.push(
          searchKnowledgeGraph(providerId, query, { allowedSites, config: configWithAuth })
        );
      }
    }

    const resultsArray = await Promise.all(remoteSearchPromises);

    // Interleave results to ensure diversity
    const allResults: any[] = [];
    const maxLen = Math.max(...resultsArray.map(r => r.length), 0);

    for (let i = 0; i < maxLen; i++) {
      for (const res of resultsArray) {
        if (i < res.length) {
          allResults.push(res[i]);
        }
      }
    }

    return NextResponse.json({
      results: allResults,
      count: allResults.length
    });
  } catch (error) {
    console.error('Search error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
