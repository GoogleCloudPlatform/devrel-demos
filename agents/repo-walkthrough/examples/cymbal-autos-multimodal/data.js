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

// 5-layer architectural graph and 7-step code walkthrough for
// GoogleCloudPlatform/devrel-demos/tree/main/data-analytics/cymbal-autos-multimodal
// Organized file-by-file around data transformations and downstream flow, with phrase-synchronized cues.

window.WALKTHROUGH_DATA = {
  repo: "GoogleCloudPlatform/devrel-demos",
  subpath: "data-analytics/cymbal-autos-multimodal",
  branch: "main",
  title: "cymbal-autos-multimodal",
  subtitle: "BigQuery Multimodal AI, Vector Search & Next.js Marketplace · Transformation & Logic Walkthrough",
  layers: [
    { id: "entry",        name: "Next.js Marketplace UI",   color: "#4285F4", accent: "#8AB4F8", bg: "rgba(66, 133, 244, 0.08)" },
    { id: "engine",       name: "Search API & Data Bridge", color: "#FBBC04", accent: "#FDD663", bg: "rgba(251, 188, 4, 0.08)" },
    { id: "agents",       name: "Deal Score & Scam AI",     color: "#FF8A65", accent: "#FFAB91", bg: "rgba(255, 138, 101, 0.08)" },
    { id: "flows",        name: "Vision & Pricing SQL",     color: "#34A853", accent: "#81C995", bg: "rgba(52, 168, 83, 0.08)" },
    { id: "capabilities", name: "GCS, IAM & Schemas",       color: "#A142F4", accent: "#C58AF9", bg: "rgba(161, 66, 244, 0.08)" }
  ],
  nodes: [
    // ROW 0: NEXT.JS MARKETPLACE UI (y = 26, x >= 200)
    {
      id: "page_home",
      label: "page.tsx",
      sub: "Marketplace & Search UI",
      path: "app/src/app/page.tsx",
      layer: "entry",
      lines: 288,
      x: 205, y: 26, w: 215, h: 58,
      role: "Renders the ranked vehicle marketplace from `cars.json` with deal-tier badges (`Hidden Gem`, `Excellent`, `Great`) and reorders listings when a shopper submits a natural-language query to `/api/search`.",
      snippet: `const getDealTier = (score: number) => {
  if (score >= 90) return { text: 'Hidden Gem', icon: '💎', badgeClass: 'badge-gem' };
  if (score >= 85) return { text: 'Excellent', icon: '🌟', badgeClass: 'badge-excellent' };
  if (score >= 70) return { text: 'Great', icon: '👍', badgeClass: 'badge-good' };
  if (score >= 50) return { text: 'Fair', icon: '😐', badgeClass: 'badge-fair' };
  return { text: 'Poor', icon: '⚠️', badgeClass: 'badge-poor' };
};`
    },
    {
      id: "page_detail",
      label: "[id]/page.tsx",
      sub: "AI Deal Breakdown View",
      path: "app/src/app/[id]/page.tsx",
      layer: "entry",
      lines: 193,
      x: 495, y: 26, w: 215, h: 58,
      role: "Displays a single vehicle's auction details alongside the 3-part AI Deal Score breakdown: Market Value savings (`price_score`), photo-based Visual Condition (`condition_score`), and Scam Authenticity (`scam_distance`).",
      snippet: `export default async function ListingDetail({ params }: { params: { id: string } }) {
  const { id } = await params;
  const car = carsData.find((c) => c.id === id);
  if (!car) notFound();
  const uiDealScore = car.deal_score ?? 50;`
    },
    {
      id: "image_carousel",
      label: "ImageCarousel.tsx",
      sub: "Auction Photo Gallery",
      path: "app/src/app/components/ImageCarousel.tsx",
      layer: "entry",
      lines: 91,
      x: 785, y: 26, w: 215, h: 58,
      role: "Interactive photo viewer embedded in `[id]/page.tsx` so shoppers can inspect every Cloud Storage auction photo that the vision pipeline analyzed.",
      snippet: `export default function ImageCarousel({ images, altText }: { images: string[], altText: string }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  if (!images || images.length === 0) {
    return <img src="/placeholder-car.jpg" alt="No Image Available" />;
  }`
    },

    // ROW 1: SEARCH API & DATA BRIDGE (y = 150, x >= 200)
    {
      id: "search_route",
      label: "route.ts",
      sub: "POST /api/search",
      path: "app/src/app/api/search/route.ts",
      layer: "engine",
      lines: 57,
      x: 205, y: 150, w: 215, h: 58,
      role: "Takes a shopper's natural-language search query from `page.tsx`, embeds the text, and searches the vehicle photo embeddings from `05_semantic_scam_detection.sql` to return the 12 closest matching auction IDs.",
      snippet: `SELECT search.base.auction_id
FROM VECTOR_SEARCH(
  TABLE \`model_dev.vehicle_images_embedded\`,
  'multimodal_embedding',
  (SELECT AI.EMBED(@searchQuery, endpoint => 'gemini-embedding-2-preview').result AS multimodal_embedding),
  top_k => 12, distance_type => 'COSINE'
) AS search ORDER BY search.distance ASC;`
    },
    {
      id: "cars_json",
      label: "cars.json",
      sub: "Enriched Vehicle Payload",
      path: "app/src/data/cars.json",
      layer: "engine",
      lines: 3526,
      x: 495, y: 150, w: 215, h: 58,
      role: "Materialized JSON dataset written by `08_export_frontend_data.py` and read by `page.tsx` and `[id]/page.tsx` so the UI loads precomputed Deal Scores, price predictions, and photo summaries instantly.",
      snippet: `[
  {
    "id": "356113",
    "title": "2017 Ford F250",
    "make": "Ford", "model": "F250", "year": 2017,
    "mileage": 94795, "transmission": "Automatic"
  }
]`
    },
    {
      id: "export_py",
      label: "08_export_frontend_data.py",
      sub: "BigQuery-to-JSON Sync",
      path: "scripts/setup/08_export_frontend_data.py",
      layer: "engine",
      lines: 78,
      x: 785, y: 150, w: 215, h: 58,
      role: "Pulls the final scored listings from `06_generative_deal_score.sql`, rewrites image URLs to the user's Cloud Storage bucket, and updates `app/src/data/cars.json` sorted from highest to lowest Deal Score.",
      snippet: `query = """
SELECT m.auction_id as id, m.predicted_market_value, m.price_score,
  m.condition as condition_score, m.authenticity_score as scam_distance,
  CAST(m.deal_score AS INT64) as deal_score, v.description, m.description_summary
FROM \`model_dev.marketplace_listings\` m
JOIN \`model_dev.vehicle_metadata\` v ON m.auction_id = v.auction_id
"""`
    },

    // ROW 2: DEAL SCORE & SCAM AI (y = 274, x >= 200)
    {
      id: "scam_sql",
      label: "05_semantic_scam_detection.sql",
      sub: "Image & Scam Vector Search",
      path: "scripts/setup/05_semantic_scam_detection.sql",
      layer: "agents",
      lines: 68,
      x: 205, y: 274, w: 215, h: 58,
      role: "Performs two vector transformations: embeds vehicle photos for live visual search in `route.ts`, and compares listing descriptions against known scam profiles to output a 0-100 `authenticity_score` for `06_generative_deal_score.sql`.",
      snippet: `CREATE OR REPLACE TABLE \`model_dev.vehicle_images_embedded\` AS
SELECT auction_id,
  AI.EMBED(STRUCT(image_ref), endpoint => 'gemini-embedding-2-preview').result AS multimodal_embedding
FROM \`model_dev.vehicle_multimodal\`
WHERE ARRAY_LENGTH(image_ref) > 0;`
    },
    {
      id: "deal_sql",
      label: "06_generative_deal_score.sql",
      sub: "Weighted Deal Score Synthesis",
      path: "scripts/setup/06_generative_deal_score.sql",
      layer: "agents",
      lines: 88,
      x: 495, y: 274, w: 215, h: 58,
      role: "Combines predicted fair market value (`04`), photo condition (`03`), seller text quality, and scam authenticity (`05`) into a 0-100 `deal_score` (40% price, 30% visual, 15% text, 15% authenticity, with an 80% penalty if authenticity < 50).",
      snippet: `AI.SCORE(
  FORMAT("Rate the vehicle condition (0-100) based ONLY on this text: '%s'", description)
) AS description_score,
-- Combine: Price (40%), Condition (30%), Description (15%), Authenticity (15%)`
    },
    {
      id: "run_all_sh",
      label: "07_run_all_ml_pipelines.sh",
      sub: "Sequential SQL Runner",
      path: "scripts/setup/07_run_all_ml_pipelines.sh",
      layer: "agents",
      lines: 48,
      x: 785, y: 274, w: 215, h: 58,
      role: "Runs the four SQL transformation stages in dependency order (`03` vision -> `04` pricing -> `05` scam detection -> `06` deal scoring) so downstream tables always have fresh upstream features.",
      snippet: `bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/03_vision_extraction.sql
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/04_predictive_pricing.sql
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/05_semantic_scam_detection.sql
bq query --use_legacy_sql=false --project_id=$PROJECT_ID < scripts/setup/06_generative_deal_score.sql`
    },

    // ROW 3: VISION & PRICING SQL (y = 398, x >= 200)
    {
      id: "vision_sql",
      label: "03_vision_extraction.sql",
      sub: "Photo Condition & Attributes",
      path: "scripts/setup/03_vision_extraction.sql",
      layer: "flows",
      lines: 57,
      x: 205, y: 398, w: 215, h: 58,
      role: "Turns raw Cloud Storage vehicle photos into structured columns: a 0-100 visual `condition` rating, a 1-sentence red-flag summary, and classified `body_style`, exterior `color`, and `interior` color used by `04`, `05`, and `06`.",
      snippet: `AI.GENERATE(
  prompt => ('Rate the condition of this car on a scale from 0-100. Output a 1 sentence description of any glaring red flags', image_ref),
  output_schema => 'condition INT64, description_summary STRING'
).* EXCEPT(full_response,status)`
    },
    {
      id: "pricing_sql",
      label: "04_predictive_pricing.sql",
      sub: "Fair Market Price Model",
      path: "scripts/setup/04_predictive_pricing.sql",
      layer: "flows",
      lines: 54,
      x: 495, y: 398, w: 215, h: 58,
      role: "Trains a pricing model on historical sales from `02_load_to_bq.sh`, blends auction metadata with the visual condition and body attributes from `03_vision_extraction.sql`, and predicts `predicted_market_value` for `06_generative_deal_score.sql`.",
      snippet: `CREATE OR REPLACE MODEL \`model_dev.car_price_model\`
OPTIONS(
  MODEL_TYPE = 'BOOSTED_TREE_REGRESSOR',
  INPUT_LABEL_COLS = ['selling_price'],
  MAX_ITERATIONS = 15, TREE_METHOD = 'HIST'
) AS SELECT * EXCEPT(vin, sale_date, market_value, seller) FROM \`model_dev.synthetic_cars\`;`
    },
    {
      id: "load_bq_sh",
      label: "02_load_to_bq.sh",
      sub: "BigQuery Dataset & Table Load",
      path: "scripts/setup/02_load_to_bq.sh",
      layer: "flows",
      lines: 81,
      x: 785, y: 398, w: 215, h: 58,
      role: "Ingests historical car sales, live auction metadata, and scam risk profiles from Cloud Storage into BigQuery and updates image links so `03`, `04`, and `05` can process them.",
      snippet: `bq load --source_format=CSV --skip_leading_rows=1 --replace \\
  --schema=data/schemas/synthetic_cars_schema.json \\
  $PROJECT_ID:$DATASET_ID.synthetic_cars gs://\${USER_BUCKET}/data/synthetic_car_data.csv`
    },

    // ROW 4: GCS, IAM & SCHEMAS (y = 522, x >= 200)
    {
      id: "conn_sh",
      label: "01_setup_api_connection.sh",
      sub: "BigQuery-to-GCS & AI Bridge",
      path: "scripts/setup/01_setup_api_connection.sh",
      layer: "capabilities",
      lines: 76,
      x: 200, y: 522, w: 188, h: 58,
      role: "Creates a BigQuery Cloud Resource connection and grants its service account permission to read Cloud Storage images and call Vertex AI models in `03`, `05`, and `06`.",
      snippet: `bq mk --connection --location=$LOCATION --project_id=$PROJECT_ID \\
  --connection_type=CLOUD_RESOURCE conn
gcloud projects add-iam-policy-binding $PROJECT_ID \\
  --member="serviceAccount:\${SERVICE_ACCT_EMAIL}" --role="roles/aiplatform.user"`
    },
    {
      id: "copy_data_sh",
      label: "00_copy_data.sh",
      sub: "GCS Bucket & Photo Staging",
      path: "scripts/setup/00_copy_data.sh",
      layer: "capabilities",
      lines: 55,
      x: 410, y: 522, w: 188, h: 58,
      role: "Provisions the project's Cloud Storage bucket, copies raw auction datasets and vehicle photos into it, and enables public read access so the Next.js UI can render the images.",
      snippet: `USER_BUCKET="cymbal-autos-\${PROJECT_ID}"
gcloud storage buckets create gs://$USER_BUCKET --location=US
gsutil iam ch allUsers:objectViewer "gs://$USER_BUCKET"
gcloud storage cp -r gs://sample-data-and-media/cymbal-autos/* gs://$USER_BUCKET/`
    },
    {
      id: "schemas_json",
      label: "vehicle_metadata_schema.json",
      sub: "BigQuery Table Schemas",
      path: "data/schemas/vehicle_metadata_schema.json",
      layer: "capabilities",
      lines: 104,
      x: 620, y: 522, w: 188, h: 58,
      role: "Defines the typed column schemas for auction listings, historical car sales, and seller risk profiles consumed by `02_load_to_bq.sh`.",
      snippet: `[
  { "name": "auction_id", "type": "STRING", "mode": "NULLABLE" },
  { "name": "item_name", "type": "STRING", "mode": "NULLABLE" },
  { "name": "images", "type": "STRING", "mode": "REPEATED" }
]`
    },
    {
      id: "teardown_sh",
      label: "teardown.sh",
      sub: "Resource Cleanup Script",
      path: "scripts/cleanup/teardown.sh",
      layer: "capabilities",
      lines: 87,
      x: 830, y: 522, w: 188, h: 58,
      role: "One-command cleanup script that empties the Cloud Storage bucket, deletes the Cloud Run frontend, revokes service account permissions, and removes the BigQuery dataset.",
      snippet: `gcloud storage rm -r gs://\${USER_BUCKET}/*
gcloud run services delete cymbal-autos-frontend --region us-central1 --quiet
bq rm --connection --force --location=$LOCATION $PROJECT_ID.$LOCATION.conn
bq rm -r -f -d $PROJECT_ID:$DATASET_ID`
    }
  ],
  edges: [
    // Row 0 <-> Row 1
    { id: "page_home>search_route",     from: "page_home",    to: "search_route",   label: "POST /api/search",      detail: "`page.tsx` sends the shopper's natural-language query to `/api/search` and reorders the grid by the returned `auctionIds`." },
    { id: "page_home>cars_json",        from: "page_home",    to: "cars_json",      label: "loads featured deals",  detail: "`page.tsx` loads pre-sorted deals from `cars.json` and filters them when search results return." },
    { id: "page_detail>cars_json",      from: "page_detail",  to: "cars_json",      label: "reads car breakdown",   detail: "`[id]/page.tsx` looks up the vehicle in `cars.json` to display Market Value, Visual Condition, and Scam Authenticity." },
    { id: "page_detail>image_carousel", from: "page_detail",  to: "image_carousel", label: "passes all_images",     detail: "`[id]/page.tsx` passes the vehicle's photo array into `<ImageCarousel />`." },
    { id: "export_py>cars_json",        from: "export_py",    to: "cars_json",      label: "writes sorted JSON",    detail: "`08_export_frontend_data.py` merges BigQuery AI scores into `app/src/data/cars.json` sorted from highest to lowest `deal_score`." },

    // Row 1 <-> Row 2
    { id: "search_route>scam_sql",      from: "search_route", to: "scam_sql",       label: "queries image vectors", detail: "`route.ts` searches the vehicle photo embeddings generated by `05_semantic_scam_detection.sql`." },
    { id: "deal_sql>export_py",         from: "deal_sql",     to: "export_py",      label: "scored listings",       detail: "`06_generative_deal_score.sql` materializes the final Deal Scores that `08_export_frontend_data.py` exports to JSON." },
    { id: "run_all_sh>deal_sql",        from: "run_all_sh",   to: "deal_sql",       label: "runs SQL steps 03..06", detail: "`07_run_all_ml_pipelines.sh` executes the four SQL transformation scripts in sequence." },

    // Row 2 <-> Row 3
    { id: "vision_sql>scam_sql",        from: "vision_sql",   to: "scam_sql",       label: "image references",      detail: "`03_vision_extraction.sql` builds the Cloud Storage image references that `05_semantic_scam_detection.sql` embeds for visual search." },
    { id: "vision_sql>pricing_sql",     from: "vision_sql",   to: "pricing_sql",    label: "visual condition",      detail: "`04_predictive_pricing.sql` merges the photo-derived condition, body style, and color from `03_vision_extraction.sql` into its pricing inputs." },
    { id: "pricing_sql>deal_sql",       from: "pricing_sql",  to: "deal_sql",       label: "predicted fair price",  detail: "`04_predictive_pricing.sql` outputs the predicted fair market value used by `06_generative_deal_score.sql` to score price savings." },
    { id: "scam_sql>deal_sql",          from: "scam_sql",     to: "deal_sql",       label: "authenticity_score",    detail: "`05_semantic_scam_detection.sql` outputs the 0-100 scam authenticity score weighted and penalized in `06_generative_deal_score.sql`." },
    { id: "load_bq_sh>pricing_sql",     from: "load_bq_sh",   to: "pricing_sql",    label: "base BQ tables",        detail: "`02_load_to_bq.sh` loads historical sales, live auction metadata, and scam profiles into BigQuery." },
    { id: "load_bq_sh>run_all_sh",      from: "load_bq_sh",   to: "run_all_sh",     label: "ready for ML SQL",      detail: "Once `02_load_to_bq.sh` loads the base tables, `07_run_all_ml_pipelines.sh` runs the SQL ML pipeline stages." },

    // Row 3 <-> Row 4
    { id: "conn_sh>vision_sql",         from: "conn_sh",      to: "vision_sql",     label: "GCS & AI access",       detail: "`01_setup_api_connection.sh` grants BigQuery permission to read Cloud Storage photos and call Vertex AI in `03_vision_extraction.sql`." },
    { id: "copy_data_sh>load_bq_sh",    from: "copy_data_sh", to: "load_bq_sh",     label: "staged bucket files",   detail: "`00_copy_data.sh` stages the raw CSVs, JSONLs, and vehicle photos in Cloud Storage for `02_load_to_bq.sh`." },
    { id: "schemas_json>load_bq_sh",    from: "schemas_json", to: "load_bq_sh",     label: "table schemas",         detail: "`02_load_to_bq.sh` uses `data/schemas/*.json` to enforce column types when loading BigQuery tables." },
    { id: "teardown_sh>load_bq_sh",     from: "teardown_sh",  to: "load_bq_sh",     label: "cleans up resources",   detail: "`teardown.sh` removes the BigQuery dataset, Cloud Resource connection, bucket objects, and Cloud Run service." }
  ],
  walkthrough: [
    {
      step: 1,
      title: "End-to-End Flow: Raw Auction Data to Buyer Marketplace",
      focusNode: "copy_data_sh",
      activeNodes: ["copy_data_sh", "vision_sql", "pricing_sql", "scam_sql", "deal_sql", "export_py", "page_home"],
      activeEdges: ["vision_sql>pricing_sql", "pricing_sql>deal_sql", "scam_sql>deal_sql", "deal_sql>export_py"],
      cues: [
        { at: 0.00, phrase: "Cymbal Autos Multimodal turns raw", nodes: ["copy_data_sh"], focus: "copy_data_sh" },
        { at: 0.30, phrase: "03 vision extraction.sql inspects", nodes: ["vision_sql"], focus: "vision_sql" },
        { at: 0.45, phrase: "04 predictive pricing.sql combines", nodes: ["pricing_sql"], focus: "pricing_sql" },
        { at: 0.60, phrase: "05 semantic scam detection.sql compares", nodes: ["scam_sql"], focus: "scam_sql" },
        { at: 0.79, phrase: "06 generative deal score.sql to produce", nodes: ["deal_sql"], focus: "deal_sql" },
        { at: 0.89, phrase: "08 export frontend data.py exports", nodes: ["export_py"], focus: "export_py" },
        { at: 0.97, phrase: "in page.tsx", nodes: ["page_home"], focus: "page_home" }
      ],
      audio: "audio/step-1.wav",
      summary: "Raw auction listings and photos (`00_copy_data.sh`) flow through three parallel BigQuery transformations - photo inspection (`03_vision_extraction.sql`), fair-price modeling (`04_predictive_pricing.sql`), and scam detection (`05_semantic_scam_detection.sql`) - which `06_generative_deal_score.sql` and `08_export_frontend_data.py` turn into a ranked marketplace in `page.tsx`.",
      narration: "Cymbal Autos Multimodal turns raw vehicle auction listings and photos into a ranked buyer marketplace. Starting in 00 copy data.sh, raw auction records and vehicle images are staged into Cloud Storage and loaded into BigQuery. From there, 03 vision extraction.sql inspects every listing's photos to score visual condition and identify vehicle attributes, while 04 predictive pricing.sql combines those visual traits with historical sales to estimate a fair market price. In parallel, 05 semantic scam detection.sql compares seller descriptions against known fraud patterns to rate listing authenticity. Those three signals come together in 06 generative deal score.sql to produce a single zero-to-one-hundred Deal Score, which 08 export frontend data.py exports for the Next.js marketplace in page.tsx."
    },
    {
      step: 2,
      title: "Data Staging, Cloud Permissions & Table Loading (`00`..`02`)",
      focusNode: "copy_data_sh",
      activeNodes: ["copy_data_sh", "conn_sh", "schemas_json", "load_bq_sh", "teardown_sh"],
      activeEdges: ["copy_data_sh>load_bq_sh", "schemas_json>load_bq_sh", "teardown_sh>load_bq_sh"],
      cues: [
        { at: 0.00, phrase: "Data preparation starts in 00 copy data.sh", nodes: ["copy_data_sh"], focus: "copy_data_sh" },
        { at: 0.28, phrase: "01 setup api connection.sh creates", nodes: ["conn_sh"], focus: "conn_sh" },
        { at: 0.56, phrase: "vehicle metadata schema.json", nodes: ["schemas_json"], focus: "schemas_json" },
        { at: 0.66, phrase: "02 load to bq.sh ingests", nodes: ["load_bq_sh"], focus: "load_bq_sh" },
        { at: 0.92, phrase: "teardown.sh reverses", nodes: ["teardown_sh"], focus: "teardown_sh" }
      ],
      audio: "audio/step-2.wav",
      summary: "`00_copy_data.sh` stages raw data and public vehicle photos in Cloud Storage; `01_setup_api_connection.sh` connects BigQuery to Cloud Storage and Vertex AI; `02_load_to_bq.sh` loads the base tables using `vehicle_metadata_schema.json` so the SQL pipelines can query them.",
      narration: "Data preparation starts in 00 copy data.sh, which copies raw auction CSVs, JSON lines, and vehicle photos into your project's Cloud Storage bucket and makes the images readable by the web app. Next, 01 setup api connection.sh creates a bridge between BigQuery, Cloud Storage, and Vertex AI so SQL queries can read raw image files and invoke multimodal models directly. Using the column definitions in vehicle metadata schema.json and its companion schema files, 02 load to bq.sh ingests the historical sales records, live auction listings, and scam reference profiles into BigQuery and rewrites every photo link to point to your bucket. When testing is finished, teardown.sh reverses all of these steps in one command."
    },
    {
      step: 3,
      title: "Turning Vehicle Photos into Structured Features (`03_vision_extraction.sql`)",
      focusNode: "vision_sql",
      activeNodes: ["conn_sh", "vision_sql", "pricing_sql", "deal_sql"],
      activeEdges: ["conn_sh>vision_sql", "vision_sql>pricing_sql"],
      cues: [
        { at: 0.00, phrase: "Using the cloud connection from 01 setup api connection.sh", nodes: ["conn_sh"], focus: "conn_sh" },
        { at: 0.11, phrase: "03 vision extraction.sql transforms unstructured", nodes: ["vision_sql"], focus: "vision_sql" },
        { at: 0.83, phrase: "for 04 predictive pricing.sql", nodes: ["pricing_sql"], focus: "pricing_sql" },
        { at: 0.95, phrase: "into 06 generative deal score.sql", nodes: ["deal_sql"], focus: "deal_sql" }
      ],
      audio: "audio/step-3.wav",
      summary: "`03_vision_extraction.sql` inspects each listing's Cloud Storage photos to extract a 0-100 visual `condition` score, a one-sentence red-flag summary, and classified `body_style`, `color`, and `interior` columns that feed into `04_predictive_pricing.sql` and `06_generative_deal_score.sql`.",
      narration: "Using the cloud connection from 01 setup api connection.sh, 03 vision extraction.sql transforms unstructured auction photos into structured columns that downstream SQL models can query. First, it links each listing's Cloud Storage image URLs into a table of live object references. Next, a multimodal prompt inspects all photos of a vehicle to assign a zero-to-one-hundred visual condition score and write a one-sentence summary of visible wear or red flags, while classification prompts label the body style, exterior color, and interior color. These visual attributes fill in missing metadata for 04 predictive pricing.sql, and the visual condition score and summary flow directly into 06 generative deal score.sql."
    },
    {
      step: 4,
      title: "Estimating Fair Market Value from History & Photos (`04_predictive_pricing.sql`)",
      focusNode: "pricing_sql",
      activeNodes: ["load_bq_sh", "vision_sql", "pricing_sql", "deal_sql"],
      activeEdges: ["load_bq_sh>pricing_sql", "vision_sql>pricing_sql", "pricing_sql>deal_sql"],
      cues: [
        { at: 0.00, phrase: "Starting from the historical sales data loaded by 02 load to bq.sh", nodes: ["load_bq_sh"], focus: "load_bq_sh" },
        { at: 0.13, phrase: "04 predictive pricing.sql trains a regression model", nodes: ["pricing_sql"], focus: "pricing_sql" },
        { at: 0.54, phrase: "extracted in 03 vision extraction.sql", nodes: ["vision_sql", "pricing_sql"], focus: "vision_sql" },
        { at: 0.69, phrase: "Running the trained model over this combined table", nodes: ["pricing_sql"], focus: "pricing_sql" },
        { at: 0.83, phrase: "which 06 generative deal score.sql compares", nodes: ["pricing_sql", "deal_sql"], focus: "deal_sql" }
      ],
      audio: "audio/step-4.wav",
      summary: "`04_predictive_pricing.sql` learns pricing patterns from historical sales (`02_load_to_bq.sh`), merges live listing metadata with the photo-derived condition and body attributes from `03_vision_extraction.sql`, and predicts a fair market baseline for `06_generative_deal_score.sql`.",
      narration: "Starting from the historical sales data loaded by 02 load to bq.sh, 04 predictive pricing.sql trains a regression model to learn how make, model, year, mileage, and vehicle condition affect selling prices. To price active auction listings, it merges structured listing fields with the photo-derived condition, body style, and color extracted in 03 vision extraction.sql, using those visual signals whenever seller metadata is incomplete. Running the trained model over this combined table produces a predicted fair market value for every car, which 06 generative deal score.sql compares against the current auction bid to measure how underpriced or overpriced each listing is."
    },
    {
      step: 5,
      title: "Visual Search Indexing & Scam Risk Scoring (`05_semantic_scam_detection.sql`)",
      focusNode: "scam_sql",
      activeNodes: ["vision_sql", "scam_sql", "search_route", "deal_sql"],
      activeEdges: ["vision_sql>scam_sql", "search_route>scam_sql", "scam_sql>deal_sql"],
      cues: [
        { at: 0.00, phrase: "Building on the image references from 03 vision extraction.sql", nodes: ["vision_sql"], focus: "vision_sql" },
        { at: 0.11, phrase: "05 semantic scam detection.sql performs two vector transformations", nodes: ["scam_sql"], focus: "scam_sql" },
        { at: 0.48, phrase: "in route.ts", nodes: ["search_route"], focus: "search_route" },
        { at: 0.53, phrase: "back in 05 semantic scam detection.sql", nodes: ["scam_sql"], focus: "scam_sql" },
        { at: 0.89, phrase: "which 06 generative deal score.sql uses", nodes: ["deal_sql"], focus: "deal_sql" }
      ],
      audio: "audio/step-5.wav",
      summary: "`05_semantic_scam_detection.sql` embeds each vehicle's photos for live natural-language search in `route.ts`, and compares seller descriptions against known scam patterns to produce a 0-100 `authenticity_score` used by `06_generative_deal_score.sql`.",
      narration: "Building on the image references from 03 vision extraction.sql, 05 semantic scam detection.sql performs two vector transformations that power both live buyer search and fraud protection. First, it converts every vehicle's photos into multimodal embeddings so images can be matched against natural-language descriptions by the live search API in route.ts. Second, back in 05 semantic scam detection.sql, it embeds each seller's written description and measures its semantic distance to a catalog of known fraudulent listing patterns. Listings whose wording closely resembles known scam scripts receive a low authenticity score, which 06 generative deal score.sql uses to penalize suspicious deals."
    },
    {
      step: 6,
      title: "Computing the Final Deal Score & Exporting JSON (`06`..`08`)",
      focusNode: "deal_sql",
      activeNodes: ["run_all_sh", "deal_sql", "export_py", "cars_json"],
      activeEdges: ["run_all_sh>deal_sql", "deal_sql>export_py", "export_py>cars_json"],
      cues: [
        { at: 0.00, phrase: "When 07 run all ml pipelines.sh executes the SQL workflow", nodes: ["run_all_sh"], focus: "run_all_sh" },
        { at: 0.15, phrase: "06 generative deal score.sql, which joins", nodes: ["deal_sql"], focus: "deal_sql" },
        { at: 0.81, phrase: "08 export frontend data.py pulls", nodes: ["export_py"], focus: "export_py" },
        { at: 0.97, phrase: "into cars.json", nodes: ["cars_json"], focus: "cars_json" }
      ],
      audio: "audio/step-6.wav",
      summary: "Run sequentially by `07_run_all_ml_pipelines.sh`, `06_generative_deal_score.sql` blends price savings (40%), photo condition (30%), seller text condition (15%), and scam authenticity (15%) into a single `deal_score`, which `08_export_frontend_data.py` exports to `cars.json`.",
      narration: "When 07 run all ml pipelines.sh executes the SQL workflow, the pipeline culminates in 06 generative deal score.sql, which joins the visual condition, predicted market value, and scam authenticity score for every vehicle. It also scores the seller's written description for mechanical condition, then blends all four signals into a single Deal Score: forty percent price advantage below market value, thirty percent photo condition, fifteen percent text condition, and fifteen percent authenticity, while slashing the final score by eighty percent if authenticity falls below fifty. Once those scores are materialized in BigQuery, 08 export frontend data.py pulls the enriched listings, updates photo URLs, and writes them sorted from best to worst deal into cars.json."
    },
    {
      step: 7,
      title: "Buyer Marketplace, Live Search & Deal Breakdown (`page.tsx` & `route.ts`)",
      focusNode: "page_home",
      activeNodes: ["cars_json", "page_home", "search_route", "page_detail", "image_carousel"],
      activeEdges: ["page_home>cars_json", "page_home>search_route", "page_detail>cars_json", "page_detail>image_carousel"],
      cues: [
        { at: 0.00, phrase: "Reading the exported dataset from cars.json", nodes: ["cars_json"], focus: "cars_json" },
        { at: 0.09, phrase: "page.tsx renders the main marketplace grid", nodes: ["page_home"], focus: "page_home" },
        { at: 0.41, phrase: "sends it to route.ts", nodes: ["search_route"], focus: "search_route" },
        { at: 0.69, phrase: "opens id page.tsx", nodes: ["page_detail"], focus: "page_detail" },
        { at: 0.95, phrase: "in ImageCarousel.tsx", nodes: ["image_carousel"], focus: "image_carousel" }
      ],
      audio: "audio/step-7.wav",
      summary: "`page.tsx` loads `cars.json` to display deal-badged listings and sends natural-language searches to `route.ts` to match query text against vehicle photo embeddings, while `[id]/page.tsx` and `ImageCarousel.tsx` show the 3-signal breakdown and auction photos.",
      narration: "Reading the exported dataset from cars.json, page.tsx renders the main marketplace grid, badging top-scoring vehicles as Hidden Gems, Excellent, or Great deals. When a shopper types a natural-language search query, page.tsx sends it to route.ts, which embeds the query text and searches the vehicle photo embeddings in BigQuery to return matching auction IDs ordered by visual similarity. Clicking any vehicle card opens id page.tsx, where the shopper sees the side-by-side breakdown of Market Value savings, Visual Condition rating, and Scam Authenticity alongside the interactive photo gallery in ImageCarousel.tsx."
    }
  ]
};
