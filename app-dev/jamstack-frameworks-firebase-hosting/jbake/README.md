# Running JBake on Firebase

To deploy a [JBake](https://jbake.org/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the JBake template to generate one. 

This requires `java`
, and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


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




## Deploy to Firebase

* Generate the application: 

    ```bash
    jbake -b
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "output".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example JBake deployment](example.png)



## Learn more

Resources: 

- https://jbake.org/
