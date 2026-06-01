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
 * @file route.ts (node)
 * @description API route handler for retrieving a specific node from the Developer Knowledge Graph.
 * Why it matters: Handles requests for detailed information about a specific documentation node.
 */

import { NextRequest, NextResponse } from 'next/server';
import { searchKnowledgeGraph } from '@/lib/dkg/dkg-api';

/**
 * Handles GET requests to retrieve a specific node from the Knowledge Graph.
 * Supports resolving remote URLs encoded in base64 within the ID.
 * 
 * @param _request The incoming Next.js request object.
 * @param params The route parameters containing the node ID segments.
 * @returns A JSON response with the node data or a 404 error.
 */
export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string[] }> }
) {
  const resolvedParams = await params;
  const idParts = resolvedParams.id;
  const id = idParts.join('/'); // Reconstruct ID from path segments

  if (id.startsWith('remote-')) {
    const suffix = id.replace('remote-', '');
    let queryUrl = '';
    try {
      const decoded = Buffer.from(suffix, 'base64').toString('utf-8');
      if (decoded.includes('.') || decoded.startsWith('http')) {
        queryUrl = decoded;
      }
    } catch (e) {
      // ignore
    }

    if (queryUrl) {
      const results = await searchKnowledgeGraph('google-cloud-dkg', queryUrl);
      const match = results.find(r => r.metadata?.originalUrl === queryUrl) || results[0];

      if (match) {
        return NextResponse.json({
          node: match,
          neighbors: []
        });
      }
    }
  }

  return NextResponse.json({ error: 'Node not found', id }, { status: 404 });
}
