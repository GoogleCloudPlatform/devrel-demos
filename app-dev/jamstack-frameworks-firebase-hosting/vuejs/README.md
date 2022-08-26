# Running VueJS on Firebase

To deploy a [VueJS](https://vuejs.org/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the VueJS template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


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




## Deploy to Firebase

* Generate the application: 

    ```bash
    npm run build
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "dist".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example VueJS deployment](example.png)



## Learn more

Resources: 

- https://vuejs.org/guide/quick-start.html
- https://vuejs.org/guide/best-practices/production-deployment.html
