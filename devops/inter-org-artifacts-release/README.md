This directory contains the code accompanying the Automatic Docker Image inter-organizational release Cloud blog post. 

Link to the blog post: https://cloud.google.com/blog/products/serverless/artifact-registry-across-your-cloud

TL;DR of the post
The specific use case is that we have at least one Container Image residing in an Artifact Registry Repository that has frequent updates to it, that need to be propagated to Artifact Registry Repositories inter-organizationally. Although the images are released to external organizations they should still be private and may not be available for public use.

Architecture Components
A) Source Artifact Registry
B) Target Artigact Registry
C) Cloud Pub/Sub Topic
D) Cloud Pub/Sub Subscripstion
E) Eventarc Trigger
F) Cloud Run Service

Contents of the Directory:

A) App.py - This file contains the variables for the source and target containers as well as the execution code that will be triggered to run based on the Pub/Sub messages and contains the following Python code. 

B) Copy_image.py: this file contains the copy command app.py will leverage in order to run the gcrane command required to copy images from source AR to target AR.

C) Dockerfile: The file to package the python code into a Docker image.

D) Imagerelease.tf: Terraform code (HCL) for instantiating the entire architecture on GCP programatically


