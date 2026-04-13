import { NextResponse } from 'next/server';
import { BigQuery } from '@google-cloud/bigquery';

// Initialize BigQuery client
// This automatically uses local gcloud auth or GOOGLE_APPLICATION_CREDENTIALS
const bigquery = new BigQuery({
  projectId: process.env.PROJECT_ID,
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { query } = body;

    if (!query || typeof query !== 'string') {
      return NextResponse.json({ error: 'Search query is required' }, { status: 400 });
    }

    // Execute the Semantic Search using Vector Search and text-embeddings models
    // Parameters map to the 03_semantic_inventory_search.sql demo file
    const sqlQuery = `
      SELECT 
        search.base.auction_id
      FROM VECTOR_SEARCH(
        TABLE \`model_dev.vehicle_images_embedded\`,
        'multimodal_embedding',
        (
          SELECT AI.EMBED(
            @searchQuery,
            endpoint => 'gemini-embedding-2-preview'
          ).result AS multimodal_embedding
        ),
        top_k => 12,
        distance_type => 'COSINE'
      ) AS search
      ORDER BY search.distance ASC;
    `;

    const options = {
      query: sqlQuery,
      location: 'US', // Matches dataset location
      params: { searchQuery: query },
    };

    // Run the query as a job
    const [rows] = await bigquery.query(options);

    // Filter to just returning a clean array of string IDs to the frontend
    const auctionIds = rows.map((row: any) => row.auction_id);

    return NextResponse.json({ auctionIds });
    
  } catch (error: any) {
    console.error('Error executing semantic search:', error);
    return NextResponse.json({ error: 'Failed to execute search' }, { status: 500 });
  }
}
