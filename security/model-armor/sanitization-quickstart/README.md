# Model Armor Sanitization Quickstart

This code sample (in Python) demonstrates how to use Google Cloud SDK libraries to call the Google Cloud Model Armor API. It provides a simple, runnable script that accepts parameters to sanitize both user prompts and model responses using predefined Model Armor templates.

## Assumptions & Prerequisites

Before running this sample, please ensure the following conditions are met:

* **Application Default Credentials (ADC)** is initialized **BEFORE** the sample is launched. You can read more about setting this up in the official [Application Default Credentials documentation](https://cloud.google.com/docs/authentication/application-default-credentials).
* The provided credentials have access to the Model Armor templates and possess the necessary IAM permissions to invoke the Model Armor API in the provided project.
* The Model Armor templates are stored in the same project for which the API is invoked. *(Note: While this sample assumes they are in the same project, this is not a strict requirement of the API itself).*

## Environment Variables

The sample pulls its configuration parameters directly from environment variables. You will need to define the following variables in your terminal before executing the code:

* `PROJECT_ID`: The Google Cloud project ID where the Model Armor templates are stored and where the Model Armor API is called.
* `LOCATION_ID`: The Google Cloud location (region) where the templates are hosted.
* `USER_PROMPT_TEMPLATE_ID`: The template ID used specifically for sanitizing a user prompt.
* `RESPONSE_TEMPLATE_ID`: The template ID used specifically for sanitizing a model response.

## How to Run

1. **Install Dependencies**  

   Ensure you have the required Google Cloud libraries installed. (If you have a `requirements.txt`, run the following):

   ```bash
   pip install -r requirements.txt
   ```

2. **Set the Environment Variables**

   Export the required parameters in your terminal. Replace the placeholder values with your actual Google Cloud resource IDs:

   ```bash
   export PROJECT_ID="your-google-cloud-project-id"
   export LOCATION_ID="your-template-location"
   export USER_PROMPT_TEMPLATE_ID="your-user-prompt-template-id"
   export RESPONSE_TEMPLATE_ID="your-response-template-id"
   ```

   > [!NOTE]
   > You can define either `USER_PROMPT_TEMPLATE_ID` or `RESPONSE_TEMPLATE_ID` or both.
   > The sample will prompt you for text to be analyzed. If you set the `RESPONSE_TEMPLATE_ID` you will be prompted for user prompt and response text and have to input at least response text.

3. **Run the Code**

   Execute the Python script:

   ```bash
   python main.py
   ```
