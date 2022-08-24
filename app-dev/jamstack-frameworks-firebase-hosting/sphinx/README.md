# Running Sphinx on Firebase

To deploy a [Sphinx](https://www.sphinx-doc.org) application to Firebase, you will need an application
based on this framework. This demo gets you to use the Sphinx template to generate one. 

This requires [python3](https://cloud.google.com/python/docs/setup), and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


### Create template application


* Install the framework:

    ```bash
    pip install sphinx sphinx-autobuild
    ```

    
    

* Create a new template application:

    ```bash
    sphinx-quickstart helloworld
    # enter prompted information, accepting defaults.

    ```




* Navigate to the created project:

    ```bash
    cd helloworld/
    ```

* Run the application locally:

    ```bash
    sphinx-autobuild . _build
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.




## Deploy to Firebase

* Generate the application: 

    ```bash
    make html
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "_build/html".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example Sphinx deployment](example.png)



## Learn more

Resources: 

- https://www.sphinx-doc.org/en/master/tutorial/getting-started.html
- https://github.com/executablebooks/sphinx-autobuild
