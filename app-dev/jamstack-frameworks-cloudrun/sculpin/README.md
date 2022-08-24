# Running Sculpin on Cloud Run

To deploy a [Sculpin](https://sculpin.io) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Sculpin template to generate one. 

This requires [php](https://www.php.net/manual/en/install.php), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Generate a new template application: 

    ```bash
    brew install composer
    composer create-project sculpin/blog-skeleton helloworld

    ```

    
    




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    vendor/bin/sculpin generate --watch --server
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For Sculpin, instead of using `vendor/bin/sculpin generate --watch --server`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    vendor/bin/sculpin generate
    ```

* Create a `package.json` in the `output_dev` folder:

    ```bash
    cat <<EOF > output_dev/package.json 
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
    gcloud run deploy sculpin-helloworld \
        --source output_dev \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Sculpin deployment](example.png)





## Learn more

Resources: 

- https://sculpin.io/getstarted/
