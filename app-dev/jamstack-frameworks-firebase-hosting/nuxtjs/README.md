# Running Nuxtjs on Firebase

To deploy a [Nuxtjs](https://nuxtjs.org/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the Nuxtjs template to generate one. 

This requires [node, npm](https://cloud.google.com/nodejs/docs/setup), and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


### Create template application


* Generate a new template application: 

    ```bash
    npx create-nuxt-app helloworld
    ```

    
    Choose defaults for all options, except for "Deployment Target" (choose "Static (Static/Jamstack hosting)")




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
    npm run generate
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

![Example Nuxtjs deployment](example.png)



## Learn more

Resources: 

- https://nuxtjs.org/docs/get-started/installation
- https://nuxtjs.org/docs/get-started/commands
