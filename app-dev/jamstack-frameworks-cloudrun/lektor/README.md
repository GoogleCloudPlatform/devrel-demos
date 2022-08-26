# Running Lektor on Cloud Run

To deploy a [Lektor](https://www.getlektor.com) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Lektor template to generate one. 

This requires [python3](https://cloud.google.com/python/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    pip install lektor
    ```

    
    

* Create a new template application:

    ```bash
    lektor quickstart
    # enter "helloworld" for project name, and accept all other defaults. 

    ```




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    lektor server
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For Lektor, instead of using `lektor server`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    lektor build -O output
    ```

* Create a `package.json` in the `output` folder:

    ```bash
    cat <<EOF > output/package.json 
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
    gcloud run deploy lektor-helloworld \
        --source output \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Lektor deployment](example.png)





## Learn more

Resources: 

- https://www.getlektor.com/docs/quickstart/
