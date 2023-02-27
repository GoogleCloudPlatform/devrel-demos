# Running SitePress on Cloud Run

To deploy a [SitePress](https://sitepress.cc/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the SitePress template to generate one. 

This requires [ruby](https://cloud.google.com/ruby/docs/setup), and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    gem install sitepress
    ```

    
    

* Create a new template application:

    ```bash
    sitepress new helloworld
    cd helloworld

    ```




* Run the application locally:

    ```bash
    sitepress server
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For SitePress, instead of using `sitepress server`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    sitepress compile
    ```

* Create a `package.json` in the `build` folder:

    ```bash
    cat <<EOF > build/package.json 
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
    gcloud run deploy sitepress-helloworld \
        --source build \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example SitePress deployment](example.png)





## Learn more

Resources: 

- https://sitepress.cc/getting-started/static
