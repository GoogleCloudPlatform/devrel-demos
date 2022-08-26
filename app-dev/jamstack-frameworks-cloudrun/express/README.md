# Running Express on Cloud Run

To deploy a [Express](https://expressjs.com/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Express template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Generate a new template application: 

    ```bash
    npx express-generator helloworld
    cd helloworld
    npm install

    ```

    
    




* Run the application locally:

    ```bash
    npm start
    ```

    The site will be available at http://localhost:3000

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.




For Node applications, it will automatically run `npm start` as the entrypoint if no other command is defined. 


Because this is a default for Express, no additional configuration is required.










## Deploy to Cloud Run

* Set the project you created earlier in `gcloud`: 

    ```bash
    gcloud config set project MYPROJECT
    ```

* Build and deploy the service to Cloud Run: 

    ```bash
    gcloud run deploy express-helloworld \
        --source . \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Express deployment](example.png)





## Learn more

Resources: 

- https://expressjs.com/en/starter/generator.html
