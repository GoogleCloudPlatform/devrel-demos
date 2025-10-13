# AI Prompt Evaluation Scripts

This project contains scripts in both Node.js and Python (Jupyter Notebook)
designed to evaluate the performance of AI prompts for a spam detection task
using the Google Gemini API. These scripts serve as a practical example for
understanding and implementing automated AI model evaluation.

This is not an officially supported Google product. This project is not
eligible for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).

This project is intended for demonstration purposes only. It is not
intended for use in a production environment.

## Project Setup

Before running either script, complete the following setup steps.

### 1. Install Dependencies

Install the necessary Node.js packages using npm:

```bash
npm install
```

### 2. Set Up Environment Variables

The scripts require a Google Gemini API key to function.

1.  Create a new file named `.env` in the root of the project directory.
2.  Add your API key to the file. For a simple value like an API key, quotes
    are not necessary:

```
GEMINI_API_KEY=YOUR_API_KEY_HERE
```

---

## Scripts

This project includes two distinct scripts for different evaluation purposes.

### 1. CI/CD Check (`ci_cd_check.js`)

This script is a fast, automated quality check that can be integrated into a
CI/CD (Continuous Integration/Continuous Deployment) pipeline.

#### Description

`ci_cd_check.js` evaluates a single, predefined prompt against a dataset of
messages (`messages.csv`). It calculates the accuracy of the AI's spam
classification and determines if it meets a specific threshold (e.g., 80%).

The script will exit with a code of `0` if the accuracy is above the threshold
(pass) or `1` if it is below (fail). This pass/fail signal is what CI/CD
systems use to determine whether to proceed with a deployment.

#### How to Run

Execute the script using its npm script:

```bash
npm run ci-cd-check
```

### 2. Prompt Comparison (`compare_prompts.js`)

This script is a more detailed tool for developers to experiment with and find
the best-performing prompt for a given task.

#### Description

`compare_prompts.js` evaluates multiple prompt templates against the
`messages.csv` dataset. For each prompt, it calculates two key metrics:

1.  **Accuracy**: Whether the AI's `is_spam` classification is correct.
2.  **Explanation Similarity**: How semantically similar the AI's explanation
    is to the "ground truth" explanation in the dataset. This is calculated
    using a local sentence-transformer model.

After evaluating all prompts, the script provides a summary for each and
recommends the best one based on a weighted score of both accuracy and
similarity.

#### How to Run

Execute the script using its npm script:

```bash
npm run compare-prompts
```

### 3. Prompt Comparison using Vertex AI Evaluation (`compare_prompts_gen_ai_evaluation_service_sdk.ipynb`)

This Jupyter Notebook provides a more in-depth, cloud-based method for evaluating and comparing prompts using the Vertex AI SDK's evaluation service.

#### Description

This notebook is designed for developers who want to leverage Google Cloud's powerful evaluation tools. It evaluates multiple prompt templates by sending them to the Gemini API and then uses the Vertex AI evaluation service to compare the generated responses against a ground truth dataset.

The key metric it calculates is **ROUGE (Recall-Oriented Understudy for Gisting Evaluation)**, which assesses the quality of the generated text by comparing it to the reference explanations.

The notebook provides a detailed, side-by-side comparison, helping developers to fine-tune their prompts for optimal performance based on quantitative metrics.

#### How to Run

This script is a Jupyter Notebook and should be run in a compatible environment like Google Colab or Vertex AI Workbench. The notebook itself contains the necessary setup instructions, including package installation and authentication with Google Cloud.

---
## The Dataset (`messages.csv`)

Both scripts use the `messages.csv` file as the source of ground truth. This
file contains sample social media posts, each with the following columns:

-   `text`: The text content of the message.
-   `spam`: A `true` or `false` value indicating if the message is spam.
-   `image_path`: An optional path to an accompanying image.
-   `expected_explanation`: A reference explanation for why a message is or is
    not spam, used by the `compare_prompts.js` script.