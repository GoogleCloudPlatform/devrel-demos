# Chatbot Web App with Streamlit and Ollama-Gemma 2 on Cloud Run

In this example, we will deploy ollama service on the cloudrun as the backend, and then deploy a service which act as the frontend using streamlit, also on cloudrun

## 1. Deploy Ollama Backend on Cloud Run

Change working directory to `./ollama-cloudrun-deploy` and see this [README.md](ollama-cloudrun-deploy/README.md)

## 2. Deploy Streamlit App

Change back working directory to example root directory `devrel-demos/ai-ml/gemma-ollama-app-streamlit`

- Set permission for created ollama cloud run service account (the one created in the `Deploy Ollama Backend` step), add cloud_run/invoker permission
- Put the service account key (json file) in the working directory. IMPORTANT NOTES: this is only for tutorial purpose, as it is not secure. The best way is to use [gcloud secret manager](https://cloud.google.com/secret-manager/docs)  
- Copy `settings.yaml.example` to `settings.yaml` and change the value respective to your ollama deployment
  - `ollama_cloudrun_service_url` key denotes the ollama cloudrun service URL. E.g. "https://ollama-gemma-gpu-xxxxxxxx.us-central1.run.app"
  - `ollama_cloudrun_service_account` key denotes the service account key (json file). For this example, we rename the key file `ollama-cloudrun-sa.json` and put it in this example directory
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

## 4. Cleaning Up

After you finished your experiments, don't forget to clean all resources:

1. Artifact Registry -> Clean the pushed image
2. Service Account -> Clean the created service account for cloudrun
3. Cloud Run -> Clean the deployed services, ollama backend and streamlit frontend