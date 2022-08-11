# Just Rack (WEBrick)

[![Run on Google Cloud](https://deploy.cloud.run/button.svg)](https://deploy.cloud.run)

According to [rack's SPEC](https://github.com/rack/rack/blob/master/SPEC.rdoc#rack-applications-):

> A Rack application is a Ruby object (not a class) that responds to `call`. It takes exactly one argument, the environment and returns an Array of exactly three values: The **status**, the **headers**, and the **body**.

So, that's all this app does. You don't *need* a web framework.

Though, they do improve things, especially in this example. Because the sample string in all these examples uses characters outside of ascii/latin-1, setting the `charset` to be utf-8 (not done by default) is required to ensure all characters display as intended, even when setting the content type to `text/html`. Compare `app.rb` and `richapp.rb`, and deploy by changing `Procfile` to specify the different filename, to see the difference.
