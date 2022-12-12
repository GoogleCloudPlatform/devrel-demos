# Running Astro on Cloud Run

To deploy a [Astro](https://astro.build/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Astro template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Generate a new template application: 

    ```bash
    npm create astro@latest
    # Use "helloworld" as your new project, choose other recommended settings

    ```

    
    




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    npm start
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For Astro, instead of using `npm start`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    npm run build
    ```

* Create a `package.json` in the `dist` folder:

    ```bash
    cat <<EOF > dist/package.json 
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
    gcloud run deploy astro-helloworld \
        --source dist \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Astro deployment](example.png)





## Learn more

Resources: 

- https://docs.astro.build/en/getting-started/
