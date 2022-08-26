# Running Flutter on Cloud Run

To deploy a [Flutter](https://flutter.dev/) application to Cloud Run, you will need an application
based on this framework. This demo gets you to use the Flutter template to generate one. 

This requires Flutter, and [gcloud](https://cloud.google.com/sdk/docs/install).



To complete this demo, you will need a [Google Cloud project](https://cloud.google.com/resource-manager/docs/creating-managing-projects#creating_a_project). 


### Create template application


* Install the framework:

    ```bash
    # https://docs.flutter.dev/get-started/install

    ```

    
    

* Create a new template application:

    ```bash
    flutter create helloworld
    cd helloworld
    flutter devices

    ```




* Run the application locally:

    ```bash
    flutter run
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.


## Configure for Cloud Run

Using [Cloud Buildpacks](https://github.com/GoogleCloudPlatform/buildpacks), 
the base language is automatically identified.


For Flutter, instead of using `flutter run`, going to use a Node web server to serve the compiled files. 

* Generate the application: 

    ```bash
    flutter build web
    ```

* Create a `package.json` in the `build/web` folder:

    ```bash
    cat <<EOF > build/web/package.json 
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
    gcloud run deploy flutter-helloworld \
        --source build/web \
        --allow-unauthenticated 
    ```

    Type "Y" for all suggested operations.


Your service will now be deployed at the URL in the deployment output.

![Example Flutter deployment](example.png)





## Learn more

Resources: 

- https://docs.flutter.dev/get-started/web
