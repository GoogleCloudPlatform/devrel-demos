# Advanced RAG Techniques - Chunking

This code sample shows the end-state of the code created in this Advanced RAG Techniques - Chunking lab. (TKTK: add link to lab when published)

Author: [Amit Maraj](https://github.com/amitkmaraj)

## Overview

This lab guides you through building a Retrieval Augmented Generation (RAG) application using Google Cloud's [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres) (with the pgvector extension) and a Gemini Large Language Model (LLM) via [Vertex AI](https://cloud.google.com/vertex-ai/docs). You will set up a vector database, ingest data using different text chunking strategies, generate embeddings, and create a retrieval mechanism to query a sample dataset, observing how chunking impacts results.

## Getting Started

### Install Requirements

You'll want to install the requirements to get started. 

```bash
pip3 install -r requirements.txt
```

### Defining values in the `.env` file

A `.env.example` file has been provided as a template for your local `.env` file. 

## Understanding `enable_pgvector.py`

Here’s a breakdown of the `enable_pgvector.py` workflow:

- **Load Configuration**: It starts by loading the database credentials and connection details from the `.env` file using `dotenv`. 
- **Establish Connection**: It uses the [Cloud SQL Python Connector](https://github.com/GoogleCloudPlatform/cloud-sql-python-connector) to securely connect to your PostgreSQL instance. This is the recommended method for connecting from applications running outside of the database's VPC network. 
- **Create an Engine**: It uses `SQLAlchemy`, a popular Python SQL toolkit, to create a database engine. This engine manages the connection pool and makes it easier to execute SQL commands. 
- **Enable Extension**: The script's primary job is to execute the `CREATE EXTENSION IF NOT EXISTS` vector; command.  This one-time setup adds all the necessary functions and data types for storing and querying vector embeddings to your database.
- **Verification**: After attempting to create the extension, the script runs a `SELECT` query to confirm that the `vector` extension is active in the `pg_extension` table. 

This script automates a crucial database setup step, ensuring your environment is ready before you start ingesting vectorized data.

### Understanding `load_and_embed_data.py`

Here’s a breakdown of the `load_and_embed_data.py` workflow:

- **Configuration and Setup**: The script begins by loading all necessary environment variables from the `.env` file and initializing the connection to Cloud SQL using the same connector and engine pattern as the previous script. 
- **Download Data**: It downloads the sample JSON data (containing text from Harry Potter books) from a public Google Cloud Storage bucket to the local Cloud Shell environment for processing. 
- **Initialize Embedding Service**: It initializes the `VertexAIEmbeddings` class, which connects to Vertex AI's `text-embedding-005` model. This service will be used to convert text chunks into numerical vector embeddings. 
- **Process Each Chunking Strategy**: The script then enters its main loop, iterating through a list of strategies: `"character"`, `"recursive"`, and `"token"`. 

    - **Chunking**: For each strategy, the `_prepare_and_chunk_documents` function is called. This function takes the raw text and uses the corresponding LangChain `TextSplitter` (e.g., `RecursiveCharacterTextSplitter`) to break the documents into smaller pieces according to the defined `CHUNK_SIZE` and `CHUNK_OVERLAP`. 

    - **Storing**: It then initializes LangChain's `PGVector` vector store, pointing it to a unique collection name for that strategy (e.g., `rag_harry_potter_recursive`). When `store.add_documents()` is called, `PGVector` sends the text chunks to the Vertex AI embedding service, receives the vector embeddings, and stores them in the specified collection (which corresponds to a table in your database). The `pre_delete_collection=True` parameter ensures each run starts fresh by deleting any old data in that collection. 

By the end of this script's run, this script will have populated your database with three separate tables of vectorized data, ready for querying.

## Understanding `query_data.py`

Here’s a breakdown of the workflow in  `query_data.py`:

- **Configuration and Setup**: Similar to the other scripts, it loads configuration from the `.env` file and establishes a connection to your Cloud SQL database. 
- **Initialize Embedding Service**: It initializes the same `VertexAIEmbeddings` service you used for ingestion. This is a crucial step because your query text must be converted into an embedding using the exact same model that was used to embed the source documents. This ensures the similarity search is comparing "apples to apples." 
- **Query Each Collection**: The script enters a loop to query the collections for the `"character"`, `"recursive"`, and `"token"` strategies.
    - **Connect to Store**: For each strategy, it initializes the `PGVector` vector store, providing the specific collection name (e.g., `rag_harry_potter_recursive`) to connect to the correct table. 
    - **Perform Search**: It uses the `store.similarity_search_with_score()` method. This takes your text query, uses the embedding service to convert it into a vector, and then searches the connected collection for the vectors (chunks) that are most similar.
    - **Display Results**: Finally, it prints the top 3 retrieved chunks for that strategy, along with a relevance score. The score indicates how similar the chunk is to your query (lower scores often mean higher similarity in cosine distance). This allows you to directly compare which strategy returned the most coherent and relevant information.