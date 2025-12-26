# 🔐 Demo: Authenticated Cloud Run Requests from Any Source

## Overview

Cloud Run services are deployed with enabled authentication by default which reject unauthenticated traffic.
While invoking the services from other Google Cloud resources is easy since they "inherit" the underlying credentials, external clients — such as local development machines, on-premises servers, or applications on other cloud — face additional challenges.

This demo shows a reliable pattern for calling such Cloud Run services from absolutely anywhere, leveraging best practices and standard Google Cloud authentication mechanisms.

For a more detailed explanation of the security principles involved, please read [Securely Call a Cloud Run Service from Anywhere](https://leoy.blog/posts/securely-call-cloud-run-service-from-anywhere/).

## Quick Start

To run the demo please follow the steps below.
Before running the steps, please review the prerequisites to ensure that you can run the demo without interruptions.

### 0. Prerequsites

To run the demo you will need the following:

* [gcloud CLI](https://docs.cloud.google.com/sdk/docs/install) installed on your machine.
* Google Cloud project that is linked to a valid billing account.
* Permissions to deploy a Cloud Run service and define IAM policies on the project.

### 1. Deploy a Cloud Run service

> [!IMPORTANT]
> The commands below use the `PROJECT_ID` environment variable as a source of the project ID.
> Set up the environment variable before you run the commands.

Deploy a simple Cloud Run service called "hello".

```bash
gcloud run deploy hello-service \
  --image "us-docker.pkg.dev/cloudrun/container/hello" \
  --region us-central1 \
  --no-allow-unauthenticated \
  --project "${PROJECT_ID}"
```

The `--no-allow-unauthenticated` flag is used to  explicitly enforce authentication.
The service is deployed into the `us-central1` region. You can change the region to be closer to your geographic location.

Once the deployment command exits, retrieve the URL of the service.

```bash
SERVICE_URL=$(gcloud run services describe hello-service \
  --region us-central1 \
  --project "${PROJECT_ID}" \
  --format 'value(status.url)')
```

If you changed the location where the service is deployed in the previous command, update the region parameter in this command accordingly.

### 2. Grant access to the service to selected credentials

Once the Cloud Run service allows only authenticated calls, the caller has to be authorized to call the service.
Grant the `roles/run.invoker` role to the selected identity.
This step shows two options. **Option A** to use a user account is better suited for developer environments and quick demos. **Option B** to use a service account is more aligned with production-ready environments.

* **Option A: Authorize user account to call the Cloud Run service**
  
  Set up the user's email:

  ```bash
  USER_EMAIL="user@org.email"
  ```

  Grant the role `roles/run.invoker` on the service to the user:

  ```bash
  gcloud run services add-iam-policy-binding hello-service \
    --region us-central1 \
    --project "${PROJECT_ID}" \
    --member="user:${USER_EMAIL}" \
    --role='roles/run.invoker'
  ```

  Make sure that you keep the location of the service the same as in the previous commands.

* **Option B: Authorize service account to call the Cloud Run service**
  
  Set up the user's email:

  ```bash
  SA_EMAIL="service_account@PROJECT_ID.iam.gserviceaccount.com"
  ```

  Grant the role `roles/run.invoker` on the service to the service account:

  ```bash
  gcloud run services add-iam-policy-binding hello-service \
    --region us-central1 \
    --project "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role='roles/run.invoker'
  ```

  Make sure that you keep the location of the service the same as in the previous commands.

Th to the identity you intend to use. Choose one of the following options based on your preferred authentication method.

### 3. Set up application default credentials (ADC) in your environment

The demo leverages [application default credentials](https://docs.cloud.google.com/docs/authentication/application-default-credentials).

> [!WARNING]
> Avoid statically store credentials in your product environment.

#### **Option A: Run in one of Google Cloud Compute environments**

Run your application on a VM, AppEngine or a serverless platform like GKE, Cloud Run or another environment (eg Dataflow).
These environments have access to the local metadata server that provides access to credentials of the service account that is associated with your compute resource.
For example, if you run your application on Cloud Run, the metadata server sets up ADC to the credentials of the service account of your Cloud Run service.
You don't need to do anything. The auth library will automatically retrieve the credentials.

#### **Option B: Authenticate with a user account's credentials**

```bash
gcloud auth application-default login
```

When you run the command it either opens a browser window or prints a long URL that you will need to open manually. Follow instructions to complete authentication. At the end the gcloud command will store the acquired credentials locally.

#### **Option C: Authenticate with service account's key**

> [!IMPORTANT]
> Please familiarize yourself with [best practices](https://docs.cloud.google.com/iam/docs/best-practices-for-managing-service-account-keys) for managing service account keys before you continue.
[Generate](https://docs.cloud.google.com/iam/docs/keys-create-delete#creating) service account key and store it in your environment.
Set up reserved environment variable to the path to the key file.

```bash
export GOOGLE_APPLICATION_CREDENTIALS='PATH/TO/SA/KEY/FILE'
```

#### **Option D: Impersonate a service account**

Use your user account to impersonate a service account:

```bash
gcloud auth application-default login --impersonate-service-account SERVICE_ACCT_EMAIL
```

The `SERVICE_ACCT_EMAIL` should be a fully qualified service account email. For example: `my-test-sa@my-project-id.iam.gserviceaccount.com` for the service account `my-test-sa` in the project `my-project-id`.

You will need to grant the `roles/iam.serviceAccountTokenCreator` role to your user account in addition to granting the `roles/run.invoker` to the service account itself:

```bash
gcloud iam service-accounts add-iam-policy-binding SERVICE_ACCT_EMAIL \
    --member="user:USER_EMAIL" \
    --role="roles/iam.serviceAccountTokenCreator"
```

### 4. Execute the demo

#### Python

> [!NOTE]
> You may consider to create a [virtual environment](https://docs.python.org/3/library/venv.html) before running the following command.

```bash
cd python
pip install -r requirements.txt
python demo.py --url "${SERVICE_URL}"
```

Mind that the `SERVICE_URL` environment variable was set in the Step 1.
The successful execution prints "`🎉 --- Response Content (First 200 chars) ---`" following first 200 symbols of the response.

#### Go

> [!NOTE]
>
> * You SHOULD use `cloud.google.com/go/auth/credentials/idtoken` package in the [`cloud.google.com/go/auth`](https://pkg.go.dev/cloud.google.com/go/auth) module. The [`google.golang.org/api/idtoken`](https://pkg.go.dev/google.golang.org/api/idtoken) package contains deprecated methods and is no longer recommended for working with Google credentials tokens.
> * There is no support for ID token of the user account by design. When developing, use [impersonated account](#option-d-impersonate-a-service-account) method

```bash
cd go
go mod download
go run demo.go --url "${SERVICE_URL}"
```

Mind that the `SERVICE_URL` environment variable was set in the Step 1.
The successful execution prints "`🎉 --- Response Content (First 200 chars) ---`" following first 200 symbols of the response.

#### Other languages

Demo clients in other languages will be provided later.

## How It Works

The demo uses Google SDK to detect current setup of [application default credentials](https://docs.cloud.google.com/docs/authentication/application-default-credentials) in your environment.
It leverages credentials set up using gcloud CLI, service account credentials configured via reserved environment variable and metadata server which will work *\*ONLY\** in environments hosted on Google Cloud.
The code acquires identity token and calls the provisioned Cloud Run service using [Authentication](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Authentication) HTTP header's Bearer method.
