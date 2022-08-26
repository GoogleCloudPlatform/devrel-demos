# Running Flutter on Firebase

To deploy a [Flutter](https://flutter.dev/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the Flutter template to generate one. 

This requires Flutter, and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


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




## Deploy to Firebase

* Generate the application: 

    ```bash
    flutter build web
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "build/web".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example Flutter deployment](example.png)



## Learn more

Resources: 

- https://docs.flutter.dev/get-started/web
