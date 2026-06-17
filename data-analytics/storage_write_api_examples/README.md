# BigQuery Storage Write API: Client Code Samples

This directory contains three Python implementations of the BigQuery Storage Write API. Each script targets a unique high-performance data ingestion scenario, demonstrating the core client patterns.

## Scenario Map

1. **Committed Mode (`fraud_detection_committed.py`)**
   - **Domain:** Credit Card Fraud Auditing.
   - **Pattern:** Writes directly to the shared `_default` stream using a persistent connection. Data is immediately queryable with at-least-once delivery semantics.
   
2. **Pending Mode (`inventory_reconcile_pending.py`)**
   - **Domain:** Multi-Warehouse Stock Reconciliation.
   - **Pattern:** Creates a transactional `PENDING` stream. Appends ledger sheets sequentially, finalizes the stream, and commits the batch atomically.
   
3. **Buffered Mode (`telemetry_buffered.py`)**
   - **Domain:** Autonomous Vehicle Telemetry.
   - **Pattern:** Creates a `BUFFERED` stream. Appends coordinates every second (hidden from queries). Performs batch flushes every 10 rows, but triggers an immediate emergency flush if a safety sensor (near-miss) goes active.

## Local Setup & Execution

The scripts are completely self-contained. They automatically check for your active Google Cloud Application Default Credentials (ADC), verify if the target BigQuery dataset and tables exist, and provision them with the correct schemas if missing.

### 1. Compile the Protobuf Schema
Ensure you have the Protocol Buffer compiler (`protoc`) installed. Compile the schema file to generate Python bindings:
```bash
protoc --python_out=. schema.proto
```

### 2. Setup Environment with `uv`
Initialize the environment and sync dependencies using `uv` (requires `uv` installed):
```bash
uv sync
```

### 3. Run the Scripts
Execute the self-contained scripts using `uv run`. You will be warned about the target GCP project and dataset location, with the option to manually override them:
```bash
uv run python fraud_detection_committed.py
uv run python inventory_reconcile_pending.py
uv run python telemetry_buffered.py
```
