
const express = require('express');
const cors = require('cors');
const { BigQuery } = require('@google-cloud/bigquery');

const app = express();
const port = 3001;

app.use(cors());
app.use(express.json());

const bigquery = new BigQuery({
    projectId: 'dq-codelab'
});

// Artworks list endpoint with search and pagination
app.get('/api/artworks', async (req, res) => {
    const { search, page = 1 } = req.query;
    const limit = 20;
    const offset = (page - 1) * limit;

    let whereClauses = ["i.gcs_url IS NOT NULL"];
    if (search) {
        // Using a simple LIKE for demonstration. For production, consider sanitizing inputs.
        whereClauses.push(`e.title LIKE '%${search.replace(/'/g, "''")}%'`);
    }

    const query = `
        SELECT
            e.object_id,
            e.title,
            e.artist_display_name,
            REPLACE(i.gcs_url, 'gs://', 'https://storage.googleapis.com/') AS image_url
        FROM
            \`dq-codelab.met.artwork_embeddings\` AS e
        LEFT JOIN
            \`bigquery-public-data.the_met.images\` AS i
            ON e.object_id = i.object_id
        WHERE
            ${whereClauses.join(' AND ')}
        ORDER BY
            e.object_id
        LIMIT ${limit}
        OFFSET ${offset};
    `;

    try {
        const [rows] = await bigquery.query({ query });
        res.json(rows);
    } catch (error) {
        console.error('ERROR:', error);
        res.status(500).send('Error fetching data from BigQuery');
    }
});

// Similar artworks endpoint
app.get('/api/similar-artworks/:objectId', async (req, res) => {
    const { objectId } = req.params;

    if (!/^[0-9]+$/.test(objectId)) {
        return res.status(400).send('Invalid objectId format. Must be an integer.');
    }
    
    const targetObjectId = parseInt(objectId, 10);

    const query = `
        WITH
            target_artwork AS (
                SELECT text_embedding
                FROM \`dq-codelab.met.artwork_embeddings\`
                WHERE object_id = @target_object_id
            ),
            similarity_scores AS (
                SELECT
                    other_artworks.object_id,
                    other_artworks.title,
                    other_artworks.artist_display_name,
                    ML.DISTANCE(
                        (SELECT text_embedding FROM target_artwork),
                        other_artworks.text_embedding,
                        'COSINE'
                    ) AS distance
                FROM
                    \`dq-codelab.met.artwork_embeddings\` AS other_artworks
                WHERE
                    other_artworks.object_id != @target_object_id
            )
        SELECT
            s.object_id,
            s.title,
            s.artist_display_name,
            s.distance,
            REPLACE(i.gcs_url, 'gs://', 'https://storage.googleapis.com/') AS image_url
        FROM
            similarity_scores AS s
        LEFT JOIN
            \`bigquery-public-data.the_met.images\` AS i
            ON s.object_id = i.object_id
        WHERE i.gcs_url IS NOT NULL
        ORDER BY
            distance ASC
        LIMIT 10;
    `;

    const options = {
        query: query,
        params: { target_object_id: targetObjectId },
    };

    try {
        const [rows] = await bigquery.query(options);
        res.json(rows);
    } catch (error) {
        console.error('ERROR:', error);
        res.status(500).send('Error fetching data from BigQuery');
    }
});


app.listen(port, () => {
    console.log(`Backend server listening at http://localhost:${port}`);
});
