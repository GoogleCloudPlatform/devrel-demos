# Developer Knowledge API demo

This open-source demo shows you how to use the Developer Knowledge API to access
machine-readable, markdown-formatted Google developer documentation. In this
demo, you will learn how to:

* Create an API key that gives you access to the Developer Knowledge API.
* Save that API key locally in the `DEVELOPER_KNOWLEDGE_API_DEMO_KEY`
  environment variable.
* Download and run this demo app locally.
* Create filters to specify which parts of the Developer Knowledge API you want
  to query. In this case, you will create filters for the Firebase and Firestore
  documentation sets.
* Query the Developer Knowledge API and review the results.

## Step 1: Obtain a Developer Knowledge API key

1. If you are not already part of the Google Developer Program,
   sign up at https://developer.google.com/programs/ to gain free access
   to Google's APIs and tools in this demo.

2. Enable the [Developer Knowledge API](https://developers.google.com/knowledge/quickstart#enable-api).

3. Create a [Developer Knowledge API key](https://developers.google.com/knowledge/quickstart#create-secure-key).

## Step 2: Run the demo app

1. Download just this demo folder using `giget`:
   ```bash
   npx -y giget@latest gh+git:GoogleCloudPlatform/devrel-demos/ai-ml/developer-knowledge-api-demo developer-knowledge-api-demo
   ```
   Navigate to the created directory:
   ```bash
   cd developer-knowledge-api-demo
   ```
   
2. Install dependencies:
   ```bash
   npm install
   ```

3. Create a `.env.local` file in the root of the project and add your
   Developer Knowledge API key
   (replace <your_api_key_here> with your actual API key):
   ```env
   DEVELOPER_KNOWLEDGE_API_DEMO_KEY=<your_api_key_here>
   ```
   
4. Run the demo app in development mode:
   ```bash
   npm run dev
   ```
   Then open [http://localhost:3000](http://localhost:3000) in your browser.


## Step 3: Experiment with the demo app

First, ensure your API key is set in `.env.local` as described in Step 2.
You can verify that the app reads it by checking the **API Key** field in
the **Sources** tab (it will be read-only).

Determine which Google developer documentation to search:

1. In the **Sources** tab, expand the **Sources** section.

2. Add the _Firebase Documentation_ source:

   *  Click the **+** button.
   *  In the **Name** field, enter `Firebase Documentation`.
   *  In the **Filter** field, enter `firebase.google.com/docs`.
   *  Click the **Save** button to save your changes.

3. Add the _Firestore Documentation_ source:

   *  Click the **+** button.
   *  In the **Name** field, enter `Firestore Documentation`.
   *  In the **Filter** field, enter `docs.cloud.google.com/firestore/native/docs`.
   *  Click the **Save** button to save your changes.

Finally, search for knowledge in your sources:

1. Click the **Search** tab.

2. In the _Search_ field, enter **Database**.

3. Review the search results. Notice how all search results come from the
   Firebase and Firestore documentation.

## Test with additional documentation sources

The Developer Knowledge API indexes documentation from many Google products. For the full list, see the [Developer Knowledge Corpus Reference](https://developers.google.com/knowledge/reference/corpus-reference). In this demo, you can include a full or partial documentation set. Here are a few you might want to try:

* **ADK** (adk.dev)
* **Android** (developer.android.com)
* **Antigravity** (antigravity.google)
* **Chrome** (developer.chrome.com)
* **Firebase** (firebase.google.com)
* **Flutter** (docs.flutter.dev)
* **Go** (go.dev)
* **Google AI** (ai.google.dev)
* **Google Cloud** (cloud.google.com and docs.cloud.google.com)
    * **BigQuery** (docs.cloud.google.com/bigquery/docs)
    * **Cloud Run** (docs.cloud.google.com/run/docs)
    * **Cloud SQL** (docs.cloud.google.com/sql/docs)
    * **GKE (Google Kubernetes Engine)** (docs.cloud.google.com/kubernetes-engine/docs)
* **Google Home** (developers.home.google.com)
* **Google Maps Platform** (mapsplatform.google.com)
