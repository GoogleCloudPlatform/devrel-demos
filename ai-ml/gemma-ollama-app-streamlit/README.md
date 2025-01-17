# Chatbot Web App with Streamlit and Ollama-Gemma 2 on Cloud Run

## Deploy Ollama on Cloud Run

## Deploy Streamlit App

- Set permission for ollama cloud run service account, add cloud_run/invoker
- Put the service account key (json file) in the working directory. NOTES: this is only for tutorial purpose, as it is not secure. The best way is to use gcloud secret manager.  
- Copy `settings.yaml.example` to `settings.yaml` and change the value respective to your ollama deployment
- run gcloud build
- run cloud run deploy

## Connect to the Chatbot Streamlit App