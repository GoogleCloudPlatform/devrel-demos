# AlloyDB Instance Manager

This tool allows you to manage and check AlloyDB instances from the command line.

## Prerequisites

- Go 1.22 or later
- A configured GCP project with the AlloyDB API enabled

## Setup

1.  Install dependencies:
    ```bash
    go mod tidy
    ```

## Usage

### Manage Instances

The `manage` command allows you to perform operations like listing, starting, stopping, deleting, and failing over AlloyDB instances.

```bash
go run main.go manage -project <your-gcp-project> -location <alloydb-location> -cluster <alloydb-cluster> -operation <operation>
```

**Arguments:**

-   `-project`: Your GCP project ID.
-   `-location`: The location of your AlloyDB instances (e.g., `us-central1`). Use `ALL` for all locations.
-   `-cluster`: The name of your AlloyDB cluster. Use `ALL` for all clusters.
-   `-operation`: The operation to perform. Available operations are:
    -   `LIST`: Lists all instances.
    -   `START`: Starts instances.
    -   `STOP`: Stops instances.
    -   `DELETE`: Deletes instances.
    -   `FAILOVER`: Fails over instances.

**Example:**

To list all instances in the `us-central1` location for the `my-cluster` cluster in the `my-gcp-project` project:

```bash
go run main.go manage -project my-gcp-project -location us-central1 -cluster my-cluster -operation LIST
```

### Check Instances

The `check` command allows you to check AlloyDB instances against a set of rules.

```bash
go run main.go check -project <your-gcp-project> -location <alloydb-location> -cluster <alloydb-cluster> -instance <alloydb-instance> -rules '<json-rules>'
```

**Arguments:**

-   `-project`: Your GCP project ID.
-   `-location`: The location of your AlloyDB instances (e.g., `us-central1`). Use `ALL` for all locations.
-   `-cluster`: The name of your AlloyDB cluster. Use `ALL` for all clusters.
-   `-instance`: The name of your AlloyDB instance. Use `ALL` for all instances.
-   `-rules`: A JSON string representing the rules to check.
-   `-debug`: Accepts values true or false to provide debug output - default false

**Example:**

To check an instance with a specific rule:

```bash
go run main.go check -project my-gcp-project -location us-central1 -cluster my-cluster -instance my-instance -rules '[{"targetFlagName":"max_connections","targetFlagValue":"4000","correctFlagValue":"1000","alertTopic":"my-alert-topic"}]' -debug true
```

## Deploy As Google Cloud Function 

Optionally deploy the package as cloud function in your project and run using scheduler to manage or check instances parameters. 


## AlloyDB Instance Management Cloud Functions - Terraform Deployment
This folder contains the Go source code and Terraform configuration to deploy two Google Cloud Functions for managing and checking AlloyDB instances.

### Infrastructure
The main.tf script will provision the following resources:

1. Three Pub/Sub Topics:

- `manage-alloydb-instances-topic`: Pub/Sub messages sent here will trigger the manage-alloydb-instances function.

- `check-alloydb-instances-topic`: Pub/Sub messages sent here will trigger the check-alloydb-instances function.

- `alloydb-instance-alerts-topic`: The check-alloydb-instances function will publish any alerts to this topic.

2. A Service Account:

- A dedicated service account (`alloydb-manager-sa`) is created for the functions to run with.

- It is granted the necessary IAM roles (`AlloyDB Admin`, `Pub/Sub Publisher`) to manage instances and publish alerts.

3. A Cloud Storage Bucket:

- A bucket is created to store the zipped Go source code for deployment.

4. Two Cloud Functions (2nd Gen):

`manage-alloydb-instances`: Deploys the ManageAlloyDBInstances Go function. It's triggered by messages on its corresponding topic.

`check-alloydb-instances`: Deploys the CheckAlloyDBInstances Go function. It's triggered by messages on its corresponding topic.

### Prerequisites
1. Terraform (v1.0+) installed.

2. Google Cloud SDK installed and authenticated (gcloud auth application-default login).

3. The project you are deploying to has billing enabled.

### How to Use
Once deployed, you can trigger the functions by publishing a JSON message to the respective Pub/Sub topics.

Example: Triggering the `check-alloydb-instances` function
1. Get the topic name:
`gcloud pubsub topics list`

2. Publish a message:

```
gcloud pubsub topics publish check-alloydb-instances-topic --message '{
  "project": "YOUR_PROJECT_ID",
  "location": "ALL",
  "cluster": "ALL",
  "instance": "ALL",
  "debug": true,
  "rules": [
    {
      "targetFlagName": "max_connections",
      "correctFlagValue": "",
      "alertTopic": "alloydb-instance-alerts-topic"
    },
    {
      "targetFlagName": "log_min_duration_statement",
      "correctFlagValue": "5000",
      "alertTopic": "alloydb-instance-alerts-topic"
    }
  ]
}'
```

Example: Triggering the `manage-alloydb-instances` function

```
gcloud pubsub topics publish manage-alloydb-instances-topic --message '{
    "project": "YOUR_PROJECT_ID",
    "location": "us-central1",
    "cluster": "my-cluster",
    "operation": "STOP"
}'
```
You can then check the function logs in the Google Cloud Console to see the output.