---
id: bq-dataprep
summary: In this codelab, you'll learn how to build a complete, low-code AI pipeline within BigQuery. You will start with a raw CSV file containing complex JSON strings, use BigQuery Data preparation to clean and structure the data without writing any code, generate vector embeddings using BigQuery ML (BQML) and a Gemini model, and finally, learn how to use these embeddings to power a real-time similarity search for an AI recommendation engine.
authors: Hyunuk Lim
categories: cloud,data,ai/ml
tags: web
feedback_link: https://github.com/googlecodelabs/feedback/issues/new?title=[bq-dataprep]%20&labels=cloud
analytics_account: UA-52746336-1
source: 1cg8DhD9AKBbqFPozHxAezP31qZd2RgZHmTsjLO1CLFA
duration: 0
layout: paginated
keywords: docType:Codelab, product:BigQuery

---

# From Raw CSV to AI Recommendations with BigQuery

[Codelab Feedback](https://github.com/googlecodelabs/feedback/issues/new?title=[bq-dataprep]%20&labels=cloud)


## Introduction



Data analysts are often faced with valuable data locked away in semi-structured formats like JSON payloads. Extracting and preparing this data for analysis and machine learning has traditionally been a significant technical hurdle, often requiring complex ETL scripts and the intervention of a data engineering team.

This codelab provides a technical blueprint for data analysts to overcome this challenge independently. It demonstrates a "low-code" approach to building an end-to-end AI pipeline. You will learn how to go from a raw CSV file in Google Cloud Storage to powering an AI-driven recommendation feature, using only the tools available within the BigQuery Studio.

The primary objective is to move beyond complex, code-heavy processes and instead establish a robust, fast, and analyst-friendly workflow for generating real business value from your data.

### **Prerequisites**

* A basic understanding of the Google Cloud Console
* Basic skills in command line interface and Google Cloud Shell

### **What you'll learn**

* How to ingest and transform a CSV file directly from Google Cloud Storage using BigQuery Data Preparation.
* How to use no-code transformations to parse and flatten nested JSON strings within your data.
* How to create a BigQuery ML remote model that connects to a Vertex AI foundation model for text embedding.
* How to use the ML.GENERATE_TEXT_EMBEDDING function to convert textual data into numerical vectors.
* How to use the ML.DISTANCE function to calculate cosine similarity and find the most similar items in your dataset.

### **What you'll need**

* A Google Cloud Account and Google Cloud Project
* A web browser such as  [Chrome](https://www.google.com/chrome/)

### **Key concepts**

* **BigQuery Data preparation:** A tool within BigQuery Studio that provides an interactive, visual interface for data cleaning and preparation. It suggests transformations and allows users to build data pipelines with minimal code.
* **BQML Remote Model:** A BigQuery ML object that acts as a bridge to a model hosted on Vertex AI (like Gemini). It allows you to invoke powerful, pre-trained AI models using familiar SQL syntax.
* **Vector Embedding:** A numerical representation of data, such as text or images. In this codelab, we'll convert text descriptions of artwork into vectors, where similar descriptions have vectors that are "closer" together in multi-dimensional space.
* **Cosine Similarity:** A mathematical measure used to determine how similar two vectors are. It's the core calculation behind our recommendation engine, used by the ML.DISTANCE function to find the "closest" (most similar) artworks.


## Setup and requirements



### **Start Cloud Shell**

While Google Cloud can be operated remotely from your laptop, in this codelab you will be using  [Google Cloud Shell](https://cloud.google.com/cloud-shell/), a command line environment running in the Cloud.

From the  [Google Cloud Console](https://console.cloud.google.com/), click the Cloud Shell icon on the top right toolbar:

<img src="img/55efc1aaa7a4d3ad.png" alt="55efc1aaa7a4d3ad.png"  width="276.00" />

It should only take a few moments to provision and connect to the environment. When it is finished, you should see something like this:

<img src="img/7ffe5cbb04455448.png" alt="7ffe5cbb04455448.png"  width="624.00" />

This virtual machine is loaded with all the development tools you'll need. It offers a persistent 5GB home directory, and runs on Google Cloud, greatly enhancing network performance and authentication. All of your work in this codelab can be done within a browser. You do not need to install anything.

### **Enable required APIs and configure environment**

Inside Cloud Shell, run the following commands to set your project ID, define environment variables, and enable all the necessary APIs for this codelab.

```
export PROJECT_ID=$(gcloud config get-value project)
gcloud config set project $PROJECT_ID
export LOCATION="us-central1"
export GCS_BUCKET_NAME="met-artworks-source-${PROJECT_ID}" # Must be a globally unique name

gcloud services enable bigquery.googleapis.com \
                       storage.googleapis.com \
                       aiplatform.googleapis.com \
                       bigqueryconnection.googleapis.com
```

### **Create a BigQuery dataset and a GCS Bucket**

Create a new BigQuery dataset to house our tables and a Google Cloud Storage bucket to store our source CSV file.

```
# Create the BigQuery Dataset in the US multi-region
bq --location=$LOCATION mk --dataset $PROJECT_ID:met_art_dataset

# Create the GCS Bucket
gcloud storage buckets create gs://$GCS_BUCKET_NAME --project=$PROJECT_ID --location=$LOCATION
```

### **Prepare and Upload the Sample Data**

Clone the GitHub repository containing the sample CSV file and then upload it to the GCS bucket you just created.

```
# Clone the repository
git clone https://github.com/GoogleCloudPlatform/devrel-demos.git

# Navigate to the correct directory
cd devrel-demos/data-analytics/dataprep

# Upload the CSV file to your GCS bucket
gsutil cp dataprep-met-bqml.csv gs://$GCS_BUCKET_NAME/
```


## From GCS to BigQuery with Data preparation



In this section, we will use a visual, no-code interface to read our CSV file from GCS, clean it, and save it as a new BigQuery table.

### **Launch Data Preparation and Connect to the Source**

1. In the Google Cloud Console, navigate to the BigQuery Studio.

<img src="img/8825270159447e89.png" alt="8825270159447e89.png"  width="470.00" />

2. In the welcome page, click Data preparation card to begin.

<img src="img/8b7b3ce147a55647.png" alt="8b7b3ce147a55647.png"  width="624.00" />

3. If this is your first time, you may need to enable required APIs. Click Enable for both the "Gemini for Google Cloud API" and the "BigQuery Unified API". Once they are enabled, you can close this panel.

<img src="img/e0a128b8b63137e6.png" alt="e0a128b8b63137e6.png"  width="607.00" />

<img src="img/1ab7db12bd624bff.png" alt="1ab7db12bd624bff.png"  width="454.00" />

4. In the main Data preparation window, under "choose other data sources", click Google Cloud Storage. This will open the "Prepare data" panel on the right.

<img src="img/5ef56d07d54abab4.png" alt="5ef56d07d54abab4.png"  width="624.00" />

5. Click the Browse button to select your source file.

<img src="img/95899fcbb7383967.png" alt="95899fcbb7383967.png"  width="624.00" />

6. Navigate to the GCS bucket you created earlier (`met-artworks-source-...`) and select the `dataprep-met-bqml.csv` file. Click Select.

<img src="img/3590d0841677ad01.png" alt="3590d0841677ad01.png"  width="450.00" />

<img src="img/107797a8f134b248.png" alt="107797a8f134b248.png"  width="408.00" />

7. Next, you need to configure a staging table. 

1. For Dataset, select the `met_art_dataset` you created. 
2. For Table name, enter a name, for example, `met_art_table`. 
3. Click Create.

<img src="img/694a7064eb1f2109.png" alt="694a7064eb1f2109.png"  width="624.00" />

### **Transform and Clean the Data**

1. BigQuery's Data preparation will now load a preview of the CSV. Find the label_details_json column, which contains the long JSON string. Click on the column header to select it.

<img src="img/345e09d8222ef0d6.png" alt="345e09d8222ef0d6.png"  width="624.00" />

2. In the Suggestions panel on the right, Gemini in BigQuery will automatically suggest transformations. Click the Apply button on the "Flattening column label_details_json" card. This will extract the nested fields (`description`, `score`, etc) into their own top-level columns.

<img src="img/a432edf49f182ea3.png" alt="a432edf49f182ea3.png"  width="357.00" />

### **Define the Destination and Run the Job**

1. In the right-hand panel, click the Destination button to configure the output of your transformation.

<img src="img/90b0d1e641d6ace9.png" alt="90b0d1e641d6ace9.png"  width="394.00" />

2. Set the destination details:

1. The Dataset should be pre-filled with `met_art_dataset`.
2. Enter a new Table name for the output: `met_flattened_data`.
3. Click Save.

<img src="img/cda9b07bfd5ff6a3.png" alt="cda9b07bfd5ff6a3.png"  width="576.00" />

3. Click the Run button, and wait until the data preparation job is completed.

<img src="img/9be3f3baecc7ee93.png" alt="9be3f3baecc7ee93.png"  width="373.21" />

4. You can monitor the job's progress in the Executions tab at the bottom of the page. After a few moments, the job will complete.

<img src="img/df820e4a5183e9b9.png" alt="df820e4a5183e9b9.png"  width="443.50" />

<img src="img/f9329c88a7fdb535.png" alt="f9329c88a7fdb535.png"  width="450.64" />


## Generating Vector Embeddings with BQML



Now that our data is clean and structured, we can use BigQuery ML to perform the core AI task: converting the textual descriptions of the artwork into numerical vector embeddings.

### **Create a BigQuery Connection**

To allow BigQuery to communicate with Vertex AI services, you must first create a BigQuery Connection.

1.  In the BigQuery Studio's Explorer panel, click the "+ Add data" button.

<img src="img/eef6c5c73cf8736.png" alt="eef6c5c73cf8736.png"  width="481.00" />

2. In the right-hand panel, use the search bar to type `Vertex AI`. Select it and then BigQuery federation from the filtered list.

<img src="img/32e9632e84dd1ae7.png" alt="32e9632e84dd1ae7.png"  width="502.76" />

<img src="img/7feedffb98bb288a.png" alt="7feedffb98bb288a.png"  width="578.50" />

3. This will open the External data source form. Fill in the following details:

* Connection ID: Enter the connection ID (e.g., `bqml-vertex-connection`)
* Location Type: Ensure Region is selected.
* Location: Select the location (e.g., `us-central1`).

<img src="img/ea840113d250fcef.png" alt="ea840113d250fcef.png"  width="624.00" />

4. Once the connection is created, a confirmation dialog will appear. Click Go to Connection or External connections in the Explorer tab. On the connection details page, copy the full ID to your clipboard. This is the identity that BigQuery will use to call Vertex AI.

<img src="img/fd0d82f3265f1def.png" alt="fd0d82f3265f1def.png"  width="624.00" />

5. In the Google Cloud Console navigation menu, go to IAM & admin &gt; IAM.

<img src="img/de8a0fe28f8dee8f.png" alt="de8a0fe28f8dee8f.png"  width="508.00" />

6. Click the "Grant access" button
7. Paste the service account you copied in the previous step in the New principals field.
8. Assign "Vertex AI user" at the Role dropdown, and click "Save".

<img src="img/8b2c89b8c97e37cc.png" alt="8b2c89b8c97e37cc.png"  width="624.00" />

This critical step ensures BigQuery has the proper authorization to use Vertex AI models on your behalf.

### Create a Remote model

In the BigQuery Studio, open a new SQL editor tab. This is where you will define the BQML model that connects to Gemini.

This statement doesn't move any data or train a new model from scratch. It simply creates a reference, or a "pointer," in BigQuery that connects to Google's powerful `gemini-embedding-001` foundation model using the connection you just authorized.

Copy the entire SQL script below and paste it into the BigQuery editor.

<img src="img/ba0a9c9d951c0f71.png" alt="ba0a9c9d951c0f71.png"  width="624.00" />

> aside negative
> 
> **⚠️ Important**
> 
> You must manually replace both instances of the placeholder `PROJECT_ID` with your actual project ID. You can find your project ID at the top of the Google Cloud Console or by running `echo $PROJECT_ID` in your Cloud Shell terminal.

```
CREATE OR REPLACE MODEL `met_art_dataset.embedding_model`
REMOTE WITH CONNECTION `us-central1.bqml-vertex-connection`
OPTIONS (endpoint = 'gemini-embedding-001');
```

Once you have updated the Project ID, click Run.

### Generate Embeddings

Now, we will use our BQML model to generate the vector embeddings. Instead of simply converting a single text label for each row, we will use a more sophisticated approach to create a richer, more meaningful "semantic summary" for each artwork. This will result in higher-quality embeddings and more accurate recommendations.

This query performs a critical pre-processing step:

* It uses a WITH clause to first create a temporary table.
* Inside it, we GROUP BY each object_id to combine all information about a single artwork into one row.
* We use the STRING_AGG function to merge all the separate text descriptions (like 'Portrait', 'Woman', 'Oil on canvas') into a single, comprehensive text string, ordering them by their relevance score.

This combined text gives the AI a much richer context about the artwork, leading to more nuanced and powerful vector embeddings.

In a new SQL editor tab, paste and run the following query:

```
CREATE OR REPLACE TABLE `met_art_dataset.artwork_embeddings` AS
WITH artwork_semantic_text AS (
  -- First, we group all text labels for each artwork into a single row.
  SELECT
    object_id,
    -- STRING_AGG combines all descriptions into one comma-separated string,
    -- ordering them by score to put the most relevant labels first.
    STRING_AGG(description, ', ' ORDER BY score DESC) AS aggregated_labels
  FROM
    `met_art_dataset.met_art_flatten_table`
  GROUP BY
    object_id
)
SELECT
  *
FROM ML.GENERATE_TEXT_EMBEDDING(
  MODEL `met_art_dataset.artwork_embedding_model`,
  (
    -- We pass the new, combined string as the content to be embedded.
    SELECT
      object_id,
      aggregated_labels AS content
    FROM
      artwork_semantic_text
  )
);
```

Once the query completes, verify the results. In the Explorer panel, find your new artwork_embeddings table and click on it. In the table schema viewer, you will see the object_id, the new ml_generate_text_embedding_result column containing the vectors, and also the aggregated_labels column that was used as the source text.

[IMAGE DESCRIPTION]

A screenshot showing the schema of the final artwork_embeddings table. The object_id, aggregated_labels, and ml_generate_text_embedding_result columns are highlighted.


## Finding Similar Artworks with SQL



With our high-quality, context-rich vector embeddings created, finding thematically similar artworks is as simple as running a SQL query. We use the ML.DISTANCE function to calculate the cosine similarity between vectors. Because our embeddings were generated from aggregated text, the similarity results will be more accurate and relevant.

1. In a new SQL editor tab, paste the following query. This query simulates what a recommendation application would do:

* It first selects the vector for a single, specific artwork (in this case, Van Gogh's "Cypresses," which has an object_id of 436535).
* It then calculates the distance between that single vector and all other vectors in the table.
* Finally, it orders the results by distance (a smaller distance means more similar) to find the top 10 closest matches.

```
WITH selected_artwork AS (
  SELECT text_embedding
  FROM `met_art_dataset.artwork_embeddings`
  WHERE object_id = "436535"
)
SELECT
  base.object_id,
  -- ML.DISTANCE calculates the cosine distance between the two vectors.
  -- A smaller distance means the items are more similar.
  ML.DISTANCE(base.text_embedding, (SELECT text_embedding FROM selected_artwork), 'COSINE') AS similarity_distance
FROM
  `met_art_dataset.artwork_embeddings` AS base, selected_artwork
ORDER BY
  similarity_distance
LIMIT 10;
```

2. Run the query. The results will show a list of object_ids, with the closest matches at the top (the original item itself will have a distance of 0). This is the core logic that powers an AI recommendation engine, and you've built it entirely within BigQuery using just SQL.


## Cleaning up your environment



To avoid incurring future charges to your Google Cloud account for the resources used in this codelab, you should delete the resources you created.

Run the following commands in your Cloud Shell terminal to remove the BigQuery Connection, the GCS Bucket, and the BigQuery Dataset.

```
# Re-run these exports if your Cloud Shell session timed out
export PROJECT_ID=$(gcloud config get-value project)
export LOCATION="us-central1"
export DATASET_ID="met_art_dataset"
export GCS_BUCKET_NAME="met-artworks-source-${PROJECT_ID}"
export BQ_CONNECTION_ID="bqml-vertex-connection"
```

```
# Delete the BigQuery Connection
gcloud bq connections delete $BQ_CONNECTION_ID --project_id=$PROJECT_ID --location=$LOCATION --quiet

# Delete the GCS bucket and its contents
gcloud storage rm --recursive gs://$GCS_BUCKET_NAME
```

### **Delete the BigQuery Dataset**

Next, delete the BigQuery dataset. This command is irreversible and uses the -f (force) flag to remove the dataset and all its tables without confirmation.

> aside negative
> 
> **⚠️ Warning:** To avoid accidental data loss, we strongly recommend you type the following command manually instead of copying and pasting, ensuring the dataset name is correct.

```
# Manually type this command to confirm you are deleting the correct dataset
bq rm -r -f --dataset $PROJECT_ID:met_art_dataset
```


## Congratulations!



You have successfully built an end-to-end, AI-powered data pipeline.

You started with a raw CSV file in a GCS bucket, used BigQuery Data Prep's low-code interface to ingest and flatten complex JSON data, created a powerful BQML remote model to generate high-quality vector embeddings with a Gemini model, and executed a similarity search query to find related items.

You are now equipped with the fundamental pattern for building AI-assisted workflows on Google Cloud, transforming raw data into intelligent applications with speed and simplicity.

### **What's Next?**

* **Build a Frontend:** Use a tool like Streamlit or Cloud Run to build a simple web application that executes the ML.DISTANCE query and visualizes the results.
* **Explore other models:** Try different embedding models available in Vertex AI by changing the ENDPOINT in your CREATE MODEL statement.
* **Automate the pipeline:** Use Cloud Composer or Cloud Workflows to schedule this entire process, from file ingestion in GCS to the creation of the final embedding table, to run automatically.
* **Read the documentation:**

  *   [Gemini CLI: your open-source AI agent](https://blog.google/technology/developers/introducing-gemini-cli-open-source-ai-agent/)

  *   [Code Sample on GitHub](https://www.github.com/GoogleCloudPlatform/devrel-demos/tree/main/data-analytics/programmatic-dq)
