# Running Jekyll on Firebase

To deploy a [Jekyll](https://jekyllrb.com/) application to Firebase, you will need an application
based on this framework. This demo gets you to use the Jekyll template to generate one. 

This requires [ruby](https://cloud.google.com/ruby/docs/setup), and [firebase](https://cloud.google.com/firestore/docs/client/get-firebase).



To complete this demo, you will need a Firebase project. You can [create a new one](https://console.firebase.google.com/u/0/?pli=1), or connect an existing [Google Cloud project](https://cloud.google.com/firestore/docs/client/get-firebase).


### Create template application


* Install the framework:

    ```bash
    gem install bundler jekyll
    ```

    
    

* Create a new template application:

    ```bash
    jekyll new helloworld
    cd helloworld
    echo "gem 'webrick'" >> Gemfile
    bundle install

    ```




* Run the application locally:

    ```bash
    bundle exec jekyll serve
    ```

    

    Enter `Ctrl+C` or `CMD+C` to stop the process.




## Deploy to Firebase

* Generate the application: 

    ```bash
    bundle exec jekyll build
    ```

* Setup Firebase: 

    ```bash
    firebase init hosting
    ```

    * In "Project Setup", select the project you configured earlier.
    * For "What do you want to use as your public directory", enter "_site".
    * Choose the default for all other options.

* Deploy to Firebase: 

    ```bash
    firebase deploy --only hosting
    ```

Your service will now be deployed at the URL in the output under "Hosting URL".

![Example Jekyll deployment](example.png)



## Learn more

Resources: 

- https://jekyllrb.com/docs/
- https://jekyllrb.com/docs/usage/
