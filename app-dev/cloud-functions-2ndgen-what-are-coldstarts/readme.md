# Visualizing Cloud Functions cold starts & warm instances

This demo illustrates the differences between cold starts and warm instances. This demo also shows how to use [global scope to reuse objects in future invocations](https://cloud.google.com/functions/docs/bestpractices/tips#use_global_variables_to_reuse_objects_in_future_invocations).

## Overview

In this demo, you'll see a Cloud Function simulate a long I/O request, e.g. a connection to a database or an API call. The Function will take about 10 seconds to respond the first time it receives a request.

Since this connection call is made outside of the Function's event handler method, it is saved in the global scope. As long as that particular instance stays in use, (e.g. continues to receive requests), any subsequent invocations to that specific instance can reuse that connection. This means that response times will be much faster because the slow connection has been cached in global scope.

## How to demo

1. Deploy the Function. A `deploy.sh` script is provided.
2. Wait about 2 minutes after deploying. A health check is performed immediately after deploying, which creates a warm instance. After a couple of minutes, the health-check instance will spin down.
3. Hit the URL, either via curl or your browser. Notice how it takes 10 seconds. This is a cold start.
4. Wait a few seconds and hit refresh. You should get an immediate response. If you happen to get another cold start, this is a second container instance spinning up just in case there are more requests coming in.
5. Go to the logs. You'll see the cold start from the health check, the cold start from your first request, and then the I'm a warm instance for the future requests.

//todo: add image

## What's next

To reduce the number of cold starts, e.g. you are predicting traffic due to Black Friday / Cyber Monday, you can try setting min instances and concurrency. More info in this [Cloud Functions 2nd gen codelab](https://codelabs.developers.google.com/codelabs/cloud-starting-cloudfunctions-v2#0)
