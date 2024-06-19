# Chatbot with Gemini Flash 1.5

Goal: To create a simple chat bot using following resoruces

* Gemini Flash 1.5: A powerful large language model from Google AI and also a Lightweight, fast and cost-efficient AI model.
* Streamlit: An open-source Python framework for data scientists and AI/ML engineers for building interactive data apps.
* Cloud Run: A fully managed platform that enables you to run your code directly on top of Google's scalable infrastructure.


## Prerequisites

* Google Chrome (browser)
* Google Cloud Project

For development environments or IDEs, the recommended option is to use Google Cloud Shell, a simple and convenient tool. Alternatively, you can set up local access to your project using the gcloud CLI and the latest version of Python.

If you are using 

## How to run?

If you wish to skip the details and host the app directly, then go to `lesson02/` and run `deploy.sh`


## Folder structure

Here is the folder structure of the repository.
```
.
├── lesson01
│   ├── deploy.sh
│   ├── Procfile
│   ├── requirements.txt
│   └── streamlit_app.py
├── lesson02
│   ├── deploy.sh
│   ├── llm.py
│   ├── Procfile
│   ├── requirements.txt
│   └── streamlit_app.py
├── LICENSE
└── README.md
```


* `deploy.sh` for deploying your code to Cloud Run
* `Procfile` has configuration for deploying Streamlit application in Cloud Run
* `requirements.txt` has required packages for this applicaiton
* `streamlit_app.py` has the Streamlit application code
* `llm.py` contains the application code found in https://github.com/GoogleCloudPlatform/python-docs-samples/tree/main/generative_ai/inference


### Chatbot Permission

* To access Gemini Flash 1.5 AI Model from your local environment, you may need to setup [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).
* 



