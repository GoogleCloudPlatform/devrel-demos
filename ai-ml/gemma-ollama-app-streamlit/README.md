# Chatbot Web App with Streamlit and Ollama-Gemma 2 on Cloud Run

## 1. Deploy Ollama Backend on Cloud Run

see this [README.md](ollama-cloudrun-deploy/README.md)

## 2. Deploy Streamlit App

- Set permission for created ollama cloud run service account (the one created in the `Deploy Ollama Backend` step), add cloud_run/invoker permission
- Put the service account key (json file) in the working directory. IMPORTANT NOTES: this is only for tutorial purpose, as it is not secure. The best way is to use gcloud secret manager.  
- Copy `settings.yaml.example` to `settings.yaml` and change the value respective to your ollama deployment
- Run cloud build

    ```console
    gcloud builds submit --tag us-central1-docker.pkg.dev/{PROJECT_ID}/{REPOSITORY_NAME}/ollama-gemma-streamlit
    ```

- Run cloud run deploy

    ```console
    gcloud beta run deploy ollama-gemma-streamlit --image us-central1-docker.pkg.dev/{PROJECT_ID}/{REPOSITORY_NAME}/ollama-gemma-streamlit --allow-unauthenticated --port 8501
    ```

    Notes that we set `--allow-unauthenticated` so that we can access the web page without any authentication. 

## 3. Connect to the Chatbot Streamlit App

After successful deployment, it we can access it on the shown Service URL. E.g

```console
https://ollama-gemma-streamlit-xxxxxxxxx.us-central1.run.app
```
