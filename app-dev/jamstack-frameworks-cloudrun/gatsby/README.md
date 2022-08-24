# Running Gatsby on Cloud Run

To deploy a [Gatsby](https://www.gatsbyjs.com/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Gatsby template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Generate a new template application: 

    ```bash
    npm init gatsby
    # Use "helloworld" for the project, enter for all other defaults, don't install any extras.

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


For Gatsby, instead of using `npm start`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    npm run build
    ```

* Create a `package.json` in the `public` folder:

    ```bash
    cat <<EOF > public/package.json 
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
    gcloud run deploy gatsby-helloworld \
        --source public \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Gatsby deployment](example.png)





## Learn more

Resources: 

- https://www.gatsbyjs.com/docs/quick-start/
- https://www.gatsbyjs.com/docs/how-to/previews-deploys-hosting#additional
