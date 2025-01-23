#!/bin/bash
# Purpose: To deploy the App to Cloud Run.

set -x

date
# Google Cloud Project ID
PROJECT=beat-the-load-balancer

# Google Cloud Region
# TODO(Developer): Update following as required # <<--------------<<--------------<<--------------
REGION=us-west4
ZONE=us-west4-a

# Deploy app from source code
gcloud run deploy beat-the-load-balancer --source . \
    --region=$REGION --project=$PROJECT \
    --allow-unauthenticated \
    --set-env-vars=SECRET_PASSWORD=iPlan2Sleep4aWeek,BACKEND_VM_MAIN=vm-main.$ZONE.c.beat-the-load-balancer.internal

# TODO(Developer): Manually update vpc-egress after this is deployed!!!
# Image: https://screenshot.googleplex.com/6d5Xv7Z9eZbtjuH

set +x