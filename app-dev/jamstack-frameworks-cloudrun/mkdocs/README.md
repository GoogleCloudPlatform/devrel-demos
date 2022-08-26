# Running MKDocs on Cloud Run

To deploy a [MKDocs](https://www.mkdocs.org/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the MKDocs template to generate one. 

This requires [python3](https://cloud.google.com/python/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    pip install mkdocs
    ```

    
    

* Create a new template application:

    ```bash
    mkdocs new helloworld
    ```




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    mkdocs serve
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For MKDocs, instead of using `mkdocs serve`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    mkdocs build
    ```

* Create a `package.json` in the `site` folder:

    ```bash
    cat <<EOF > site/package.json 
    { 
      "scripts": { "start": "http-server" },
      "dependencies": { "http-server": "*" }
    }
    EOF
    ```

    *This is a scripting technique where all the text between `EOF` is written to the file.*





## Deploy to Cloud Run

* Set the project you created earlier in `gcloud`: 

    ```bash
    gcloud config set project MYPROJECT
    ```

* Build and deploy the service to Cloud Run: 

    ```bash
    gcloud run deploy mkdocs-helloworld \
        --source site \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example MKDocs deployment](example.png)





## Learn more

Resources: 

- https://www.mkdocs.org/getting-started/
