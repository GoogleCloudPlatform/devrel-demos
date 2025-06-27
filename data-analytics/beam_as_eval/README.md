# LLM Evaluation as a Pipeline with Apache Beam and Google Cloud Dataflow

This repository contains an advanced Apache Beam pipeline that demonstrates a multi-stage evaluation process using Google's Gemini LLM. The pipeline reads data, performs an initial classification, verifies the accuracy of that classification, and then performs windowed, stateful analysis on the results.

## Finished Code
Gemini_Beam_Eval.py contains the entire pipeline. 

You can run this pipeline locally using the `DirectRunner` for testing, or on Google Cloud Dataflow for scale.

**1. Install Dependencies:**
```bash
pip install "apache-beam[gcp]" google-cloud-aiplatform
```

**2. Authenticate with Google Cloud:**
```bash
gcloud auth application-default login
gcloud config set project YOUR_GCP_PROJECT_ID
```

**3. Run in Test Mode (Local):**
This mode uses in-memory data and is useful for quick local testing without Pub/Sub or Dataflow.
```bash
python Gemini_Beam_Eval.py \
  --project YOUR_GCP_PROJECT_ID \
  --location us-central1 \
  --model_name gemini-2.5-flash \
  --test_mode \
  --runner DirectRunner
```

**4. Run on Dataflow (Production):**
This mode reads from a Pub/Sub topic and executes on Google Cloud Dataflow.
Replace `YOUR_GCP_PROJECT_ID`, `YOUR_INPUT_TOPIC`, `YOUR_GCP_REGION`, and `YOUR_GCS_BUCKET` with your actual values.
```bash
python Gemini_Beam_Eval.py \
  --project YOUR_GCP_PROJECT_ID \
  --input_topic "projects/YOUR_GCP_PROJECT_ID/topics/YOUR_INPUT_TOPIC" \
  --location us-central1 \
  --model_name gemini-2.5-flash \
  --runner DataflowRunner \
  --region YOUR_GCP_REGION \
  --temp_location "gs://YOUR_GCS_BUCKET/temp" \
  --streaming 
```

## Tutorial Structure

The pipeline code is structured as a tutorial with distinct, incremental steps. This allows you to follow along and implement the logic for each part of the pipeline sequentially.

In complete - you will find all of the code for that step in it's executable format. 
For a challenge, try to write the code in the incomplete section, each section will have the previous section filled out and completed. 

Each step is clearly marked in the code with comments like:

```python
##### START STEP X #####
...
#### END STEP X ####
```

## Pipeline Flow

The pipeline executes the following sequence of operations:

### Step 1: Input
The pipeline begins by creating a `PCollection`. In `test_mode`, it uses a predefined list of dictionaries (`TEST_DATA`). In a production scenario, it reads JSON messages from a Pub/Sub topic. Timestamps are explicitly assigned to each element to enable event-time processing.

### Step 2: Classification with Gemini
The first `RunInference` transform, labeled **'ClassifyWithGemini'**, takes each input element. It uses the `GeminiModelHandler` to send the element's text to the Gemini API for an initial classification into categories like `SQL GENERATOR`, `HELPER`, etc.

### Step 3: Accuracy Verification
The results from the classification step are then passed to a second `RunInference` transform, **'VerifyAccuracy'**. This step uses a specialized `GeminiAccuracyModelHandler` to perform a second LLM call. This call asks Gemini to evaluate and score the accuracy of the initial classification on a scale from 0.0 to 1.0, based on the original prompt and the generated text.

### Step 4: Windowing
The results from the accuracy check, which now include the original data, the classification, and an accuracy score, are grouped into 60-second fixed windows using `beam.WindowInto`. This prepares the data for time-based aggregation.

### Step 5: Stateful Counting
A stateful `DoFn` (`StatefulCountFn`) processes the windowed data. It specifically counts the number of "bad" results (where the accuracy score is below a certain threshold) and uses Beam's `BagState` to collect the associated prompts and texts for those bad results. This step demonstrates how to use Beam's powerful state and timer APIs for complex, per-window aggregations.
