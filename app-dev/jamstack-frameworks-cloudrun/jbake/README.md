# Running JBake on Cloud Run

To deploy a [JBake](https://jbake.org/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the JBake template to generate one. 

This requires `java`
, and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    curl -s "https://get.sdkman.io" | bash
    sdk install jbake

    ```

    
    

* Create a new template application:

    ```bash
    mkdir helloworld && cd helloworld
    jbake -i

    ```




* Run the application locally:

    ```bash
    jbake -b -s
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For JBake, instead of using `jbake -b -s`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    jbake -b
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
    gcloud run deploy jbake-helloworld \
        --source output \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example JBake deployment](example.png)





## Learn more

Resources: 

- https://jbake.org/
