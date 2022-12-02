# Deploy to Cloud Run using GitHub Actions and Workload Identity Federation

## Introduction
In this tutorial, we'll configure a GitHub repo to use Workload Identity Federation to deploy a Cloud Run service whenever a merge happens on the default branch.

This tutorial is a combination of the following technologies: 

 * The [deploy-cloudrun](https://github.com/google-github-actions/deploy-cloudrun) GitHub action
 * Terraform, and the [`gh-oidc` Terraform module](https://github.com/terraform-google-modules/terraform-google-github-actions-runners)
 * [Source based Cloud Run deploys](https://cloud.google.com/run/docs/deploying-source-code)

This walkthrough requires a number of dependencies, including `gcloud`, and `terraform`. All of which are available in the Google Cloud Shell environment. 

## Project Setup

Before you begin, you will need a Google Cloud project.

1. <walkthrough-project-setup billing="true"></walkthrough-project-setup>

1. <walkthrough-enable-apis apis="cloudresourcemanager.googleapis.com,cloudbuild.googleapis.com"></walkthrough-enable-apis>

1. Navigate to the location with the Terraform configuration is stored. 

    ```bash
    cd app-dev/github-actions-wif-cloudrun
    ```

## Configuring Workload Identity Federation 


To use the script, you will need to set a number of values for the `gcloud` and `terraform` tools to reference.

1. Configure the Project and Region variables.

    ```bash
    export PROJECT_ID=<walkthrough-project-id/>
    export REGION=us-central1
    ```

1. Configure your GitHub repo values and Cloud Run service name:

    ```
    export GITHUB_REPO=youruser/yourrepo
    export DEFAULT_BRANCH=main
    export SERVICE=helloworld
    ```

    The `GITHUB_REPO` should be in the form `YourGitHubUser/YourRepo`, or `YourGitHubOrg/YourRepo`.

1. Run the script to setup Workload Identity Federation: 

    ```bash
    bash automate.sh
    ```

## Configure GitHub

With the Workload Identity Federation configured, you can now configure your GitHub repo. 

1. Export the GitHub workflow configuration, using the values you've defined:

    ```bash
    cat github_action.template.yaml | envsubst
    ```

1. Add the file to your repo's main branch and push the change.
1. On the GitHub website, go to your repo and click the Actions tab.
1. Note the running action.

Your repo will now be deployed, initially as a private service. 

## Making your site live

Your service will be deployed as a private service, so you will not be able to view it publicly, yet. 

You can try out your service before it's live: 

1. Find the service URL through the `gcloud` cli: 
    ```bash
    gcloud run services list

    export SERVICE_URL=$(gcloud run services describe SERVICE --region REGION --format "value(status.url)")
    echo Service deployed to $SERVICE_URL
    ```
1. Use `curl` to GET the service, using your `gcloud` identity: 

    ```bash
    curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" $SERVICE_URL
    ```

To make your service live: 

1. Add the IAM to allow all users access: 
    ```
    gcloud run services add-iam-policy-binding \
        SERVICE --region REGION \
        --member allUsers --role roles/run.invoker 
    ```

## Conclusion

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

You're done!

Here's what to do next:

* Learn more about [`deploy-cloudrun`](https://github.com/google-github-actions/deploy-cloudrun)
* Learn more about [Cloud Run](https://cloud.run/)