# Running VueJS on Cloud Run

To deploy a [VueJS](https://vuejs.org/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the VueJS template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    npm init vue@latest
    # Use "helloworld" for the project name
    # Press Enter for all other defaults. 

    ```

    
    

* Create a new template application:

    ```bash
    npm install
    ```




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    npm run dev
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For VueJS, instead of using `npm run dev`, going to use a Node web server to serve the compiled files. 

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
    gcloud run deploy vuejs-helloworld \
        --source dist \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example VueJS deployment](example.png)





## Learn more

Resources: 

- https://vuejs.org/guide/quick-start.html
- https://vuejs.org/guide/best-practices/production-deployment.html
