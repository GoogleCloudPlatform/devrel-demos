# Running MKDocs on Firebase

To deploy a [MKDocs](https://www.mkdocs.org/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the MKDocs template to generate one. 

This requires [python3](https://cloud.google.com/python/docs/setup), and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


### Create template application


* Install the framework:

    ```bash
    pip install mkdocs
    ```

    
    

* Create a new template application:

    ```bash
    mkdocs new helloworld
    ```




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    mkdocs serve
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.




## Deploy to Firebase

* Generate the application: 

    ```bash
    mkdocs build
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "site".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example MKDocs deployment](example.png)



## Learn more

Resources: 

- https://www.mkdocs.org/getting-started/
