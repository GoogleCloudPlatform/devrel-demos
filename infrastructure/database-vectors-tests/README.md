# Database Vectors Tests

This directory contains database performance and evaluation utilities for vector similarity search databases. Currently, it includes SQL scripts and stored procedures for **PostgreSQL** using the `pgvector` extension to benchmark search latency/throughput and evaluate vector search recall.

## Directory Structure

```text
database-vectors-tests/
├── LICENSE
├── README.md
└── postgresql/
    ├── benchmark_vector_search.sql
    └── evaluate_vector_recall.sql
```

## Scripts

### `postgresql/benchmark_vector_search.sql`
Defines a stored procedure `benchmark_vector_search` that evaluates the latency and throughput (queries per second - QPS) of vector search in PostgreSQL.
* **Warmup Loop:** Performs a warmup run to avoid cold cache penalty.
* **Repetition Loop:** Repeats search queries over the database for a specified number of times to calculate average, minimum, and maximum search latency, as well as overall throughput.
* **Sampling:** Selects up to 100 random vectors from the specified table to serve as target query vectors.
* **Assumptions:** It assumes the vector column name in the database table is `d` and uses the cosine distance operator (`<=>`).

### `postgresql/evaluate_vector_recall.sql`
Defines a stored procedure `evaluate_vector_recall` that calculates the **Recall@K** metric of approximate vector search indexes (such as HNSW or IVFFlat) compared to exact search (ground truth).
* **Exact Search (Ground Truth):** Disables index scans and forces a sequential scan to determine true nearest neighbors.
* **Approximate Search:** Enables index scans to query using the defined vector index.
* **Recall Calculation:** Measures the overlap of IDs returned by both queries and computes `|Approx ∩ Exact| / K`.
* **Summary Metrics:** Returns average, minimum, and maximum recall rates across all sampled query vectors.

---

## Installation Procedures

### Prerequisites
* A PostgreSQL instance with `pgvector` installed and enabled.

### 1. Enable `pgvector`
Connect to your PostgreSQL database and run the following command to enable the extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Load the Stored Procedures
Execute the SQL files to create the stored procedures in your target database.

Using `psql`:
```bash
psql -h <host> -U <user> -d <database> -f postgresql/benchmark_vector_search.sql
psql -h <host> -U <user> -d <database> -f postgresql/evaluate_vector_recall.sql
```

Or copy the contents of the `.sql` scripts directly and execute them within your database client (e.g., pgAdmin, Cloud SQL Studio, DBeaver, etc.).

---

## Execution Procedures

### 1. Running the Benchmark
Call the `benchmark_vector_search` procedure. Ensure your table has a vector column named `d` containing valid vectors.

```sql
CALL benchmark_vector_search(
    n_repetitions := 5,         -- Number of benchmark repetitions (excluding warmup)
    table_name_param := 'items', -- Name of the table to benchmark
    vector_dimensions := 768    -- Expected vector dimensions
);
```

#### Sample Output
```text
NOTICE:  Starting vector similarity search benchmark...
NOTICE:  Target table: items, Repetitions: 5, Expected dimensions: 768
NOTICE:  Dimension validation successful.
NOTICE:  Selecting 100 random vectors for sampling from items...
NOTICE:  Starting main benchmark loop...
NOTICE:  Warmup Repetition: Avg Latency = 14.321 ms (Min: 4.120 ms, Max: 62.451 ms) | QPS: 1395.2
NOTICE:  Repetition 1/5: Avg Latency = 3.250 ms (Min: 2.100 ms, Max: 15.654 ms) | QPS: 3076.9
...
NOTICE:  ------------------------------------------------------------------------
NOTICE:  Benchmark finished successfully.
NOTICE:  Total queries executed: 500 (excluding warmup)
NOTICE:  Total execution time:   0.162 seconds (excluding warmup)
NOTICE:  Throughput (overall):   3086.4 QPS (excluding warmup)
NOTICE:  ------------------------------------------------------------------------
NOTICE:  Latency Stats (excluding warmup):
NOTICE:  Average: 3.240 ms
NOTICE:  Minimum: 2.050 ms
NOTICE:  Maximum: 16.421 ms
NOTICE:  ------------------------------------------------------------------------
```

### 2. Evaluating Recall
Call the `evaluate_vector_recall` procedure. You can specify custom column names, `K` parameters, and sample sizes.

```sql
CALL evaluate_vector_recall(
    table_name_param := 'items', -- Name of the table to evaluate
    vector_dimensions := 768,    -- Expected vector dimensions
    vector_col_param := 'd',     -- (Optional) Name of the vector column (default 'd')
    id_col_param := 'id',        -- (Optional) Name of the primary key/ID column (default 'id')
    k_param := 5,                -- (Optional) Number of nearest neighbors to retrieve (default 5)
    sample_size_param := 100     -- (Optional) Number of random query vectors to sample (default 100)
);
```

#### Sample Output
```text
NOTICE:  Starting vector similarity search recall evaluation...
NOTICE:  Target table: items, Expected dimensions: 768
NOTICE:  Parameters - Vector Column: d, ID Column: id, K: 5, Sample Size: 100
NOTICE:  Selecting 100 random vectors for sampling from items...
NOTICE:  ------------------------------------------------------------------------
NOTICE:  Recall Evaluation Finished.
NOTICE:  Total queries evaluated: 100
NOTICE:  Average Recall@5:        98.40%
NOTICE:  Minimum Recall@5:        80.00%
NOTICE:  Maximum Recall@5:        100.00%
NOTICE:  ------------------------------------------------------------------------
```


## License

All code in this repository is licensed under the Apache 2.0 License. See [LICENSE](./LICENSE) for more information.