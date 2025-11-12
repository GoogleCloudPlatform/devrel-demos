# Creating a notification pipeline with BigQuery and Google Chat

This repository contains the notebook code for a demonstration of a notification pipeline using BigQuery Studio notebooks.

It's an automation pipeline that monitors an [RSS feed](https://docs.cloud.google.com/feeds/bigquery-release-notes.xml), uses [BigQuery](https://docs.cloud.google.com/bigquery/docs/introduction) to track what it's already seen, calls the [Gemini API in Vertex](https://cloud.google.com/vertex-ai/generative-ai/docs) to generate practical onboarding suggestions, and then posts them to [Google Chat](https://workspace.google.com/products/chat/), all orchestrated from a scheduled [BigQuery Studio notebook](https://docs.cloud.google.com/bigquery/docs/notebooks-introduction).

This demo is the subject of a blog post, which can be found here: TBD

## Running the Demo

This demo requires setup across Google Chat and Google Cloud Platform. 

### **Prerequisites**

Before you begin, you'll need:

* A [Google Workspace account](https://support.google.com/a/answer/6043576). The ability to add webhooks to a Google Chat space is a Google Workspace feature and is (unfortunately\!) not available for regular consumer Gmail accounts.  
* A [Google Cloud project](https://cloud.google.com/apis/docs/getting-started#creating_a_google_project) with [billing enabled](https://cloud.google.com/billing/docs/how-to/modify-project).  
* The [BigQuery, Vertex AI, and Secret Manager APIs enabled](https://console.cloud.google.com/flows/enableapi?apiid=bigquery.googleapis.com,aiplatform.googleapis.com,secretmanager.googleapis.com) in your Google Cloud project.  
* Sufficient [permissions on your account](https://docs.cloud.google.com/iam/docs/granting-changing-revoking-access#multiple-roles-console) or a service account. For this guide, we'll assume you are running with credentials that have the BigQuery Admin, Vertex AI User, and Secret Manager Admin roles.

### **Part 1: Set up your Google Chat destination**

First, we need a destination for our notifications. We'll create a Google Chat space and generate a webhook URL.

1. Go to [chat.google.com](https://chat.google.com).  
2. Next to "Spaces," click the three-dots and then select **Create a Space**.
3. Give your space a name, like "BigQuery Releases," and a description.  
4. Once created, click the space name at the top and select **Apps & Integrations**.
5. Click **Add Webhooks**.  
6. Give the webhook a name (e.g., "BQ Notifier") and an optional avatar.  
7. Click **Save**. A dialog will appear with the webhook URL. **Copy this URL** and save it somewhere safe for the next step.

More information on webhooks can be found in the [Google Chat documentation](https://support.google.com/a/answer/7651360).

### **Part 2: Secure your webhook with Secret Manager**

It's a best practice to never paste sensitive URLs or keys directly into code. We'll store our new webhook URL securely in [Secret Manager](https://cloud.google.com/secret-manager/docs/creating-and-accessing-secrets).

1. In the [Google Cloud Console](https://console.cloud.google.com/), check to make sure your project is selected at the top of the screen. 
2. Enable the Secret Manager API by [clicking here](https://console.cloud.google.com/apis/enableflow;apiid=secretmanager.googleapis.com).  
3. Navigate to [**Secret Manager**](https://console.cloud.google.com/security/secret-manager) by searching for it in the search bar at the top of the Cloud Console.
4. Click **\+ Create Secret**.  
5. Give the secret a name. The notebook code (see next step) expects ```chat-webhook-url``` , so it's best to use that.  
6. In the "Secret value" field, paste the Google Chat webhook URL you copied earlier.
7. Leave the other settings as default and click **Create Secret**.

### **Part 3: The automation notebook**

This is where the magic happens. We'll use a [BigQuery Studio](https://cloud.google.com/bigquery/docs/notebooks-introduction) notebook to run all the steps as Python code. This notebook will perform all the logic: fetching, filtering, enriching, and posting.

The first step is to load the notebook into our BigQuery Studio environment:

1. Click [this link](https://console.cloud.google.com/bigquery/import?url=https://github.com/GoogleCloudPlatform/devrel-demos/blob/main/data-analytics/chat-notifications/bq_releases_chat_notification.ipynb) to open a new window in the Google Cloud console with a preview of the notebook.  
2. Click **Upload** to add the notebook to your BigQuery Studio workspace.
3. Once the notebook loads, click **Connect** in the top-right corner to connect to a runtime.

And yes\! Gemini wrote 100% of this code\! (with a few back and forths, asking it to refine things, and sending a few error messages to help it make adjustments)

### **Part 4: Test and schedule the notebook**

The last step is to test the notebook and then set it up to [run automatically](https://docs.cloud.google.com/bigquery/docs/orchestrate-notebooks) so you never miss an update.

1. In the notebook, **run all the cells manually** one time to ensure everything is working correctly. You should see notifications appear in your Google Chat space for any BigQuery release notes from the last 7 days (this is the default lookback period set in the notebook).
2. Once you've confirmed it works, click the **Schedule** button at the top of the notebook interface.
3. Give the schedule a name, like `bigquery_releases_to_chat`.  
4. Choose to execute with your user credentials (or a service account with the [Secret Accessor](https://docs.cloud.google.com/iam/docs/roles-permissions/secretmanager#secretmanager.secretAccessor), BigQuery Admin, and Vertex AI User roles)  
5. Under Cloud Storage bucket, click **Browse** and then click the "Create new bucket" icon and provide a unique bucket name, such as `scheduled-notebooks-[project name]`.  
6. Set the **Frequency**. You can choose "Daily" or use a "Custom" [cron schedule](https://docs.cloud.google.com/scheduler/docs/configuring/cron-job-schedules) (e.g., `0 5,7,9,11,13,15,17 * * *` which is what I used to run every two hours between 5am-5pm).  
7. Set your desired **Timezone**.  
8. Click **Create Schedule**.

That's it\! Your automation is now live and will post new, AI-enriched BigQuery feature releases directly to your chat space.
