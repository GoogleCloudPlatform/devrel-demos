# Building a Governed Iceberg Lakehouse with BigLake and Dataplex

This repository contains the companion source code for the Google Cloud Codelab: **[Building a Governed Iceberg Lakehouse with BigLake and Dataplex](https://codelabs.developers.google.com/governed-lakehouse-compute-delegation)**

This lab demonstrates how to build a governed Data Lakehouse using Apache Iceberg, BigQuery, and Dataplex, focusing on enforcing dynamic data masking policies across completely different execution engines (BigQuery SQL and Apache Spark).

## Repository Structure

```text
data-analytics/governed-lakehouse/
├── README.md                 # This documentation file
├── requirements.txt          # Required Python packages for Dataplex and BigQuery APIs
├── 1_create_taxonomy.py      # Script to create a Dataplex Taxonomy and Policy Tag
├── 2_create_masking.py       # Script to create a BigQuery Data Policy (Masking Rule)
├── 3_grant_access.py         # Script to grant Fine-Grained Reader IAM roles
├── 4_attach_tag.py           # Script to attach the Policy Tag to a BigQuery Iceberg table schema
├── read_transactions.py      # PySpark script to test compute delegation via Dataproc Serverless
└── cleanup_governance.py     # Teardown script to remove all created governance resources
```

### File Details

* **`requirements.txt`**: Contains the necessary Google Cloud Python SDKs (`google-cloud-datacatalog`, `google-cloud-bigquery-datapolicies`, `google-cloud-bigquery`).
* **`1_create_taxonomy.py`**: Initializes the logical governance containers in Dataplex (Taxonomy: `BusinessCritical`, Policy Tag: `RestrictedFinancial`).
* **`2_create_masking.py`**: Uses a stateless API lookup to find the created Policy Tag, creates an `ALWAYS_NULL` data masking policy, and binds the Analyst persona to the masked reader role.
* **`3_grant_access.py`**: Looks up the Policy Tag and explicitly grants the Manager persona and the Current User the `Fine-Grained Reader` role so they can see the unmasked raw data.
* **`4_attach_tag.py`**: Modifies the BigLake Iceberg table (`transactions`) schema by attaching the Dataplex Policy Tag to the `amount` column.
* **`read_transactions.py`**: A PySpark job submitted to Dataproc Serverless. It reads the governed BigQuery table via the BigQuery Storage API to prove that Dataplex policies are engine-agnostic and cannot be bypassed.
* **`cleanup_governance.py`**: Safely deletes the Data Policy and Taxonomy created during the lab to prevent unexpected billing.

## Downloading the Code in Cloud Shell

To minimize storage usage in your Cloud Shell, use the following sparse-checkout method to download only this specific folder rather than the entire `devrel-demos` repository:

```bash
# Perform a shallow clone to get only the latest repository structure without the full history
git clone --depth 1 --filter=blob:none --sparse https://github.com/GoogleCloudPlatform/devrel-demos.git

# Navigate into the repo and specify the specific folder to download
cd devrel-demos
git sparse-checkout set data-analytics/governed-lakehouse
cd data-analytics/governed-lakehouse
```

## Python Environment Setup

Before running the Python scripts during the Codelab, initialize an isolated virtual environment and install the dependencies:

```bash
# Create and activate a virtual environment
python3 -m venv lakehouse_env
source lakehouse_env/bin/activate

# Install required SDKs
pip install -r requirements.txt
```