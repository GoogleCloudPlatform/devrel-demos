#!/bin/bash

echo "Running the script,.. completed!"
# Debug mode - on
set -x

export LOCATION="asia-south1-c"
export DATE_SUFFIX=`date +'%Y-%m-%d'`

gcloud compute machine-images create vm-wh01-backup-${DATE_SUFFIX}  --source-instance=vm-wh01 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh02-backup-${DATE_SUFFIX}  --source-instance=vm-wh02 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh03-backup-${DATE_SUFFIX}  --source-instance=vm-wh03 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh04-backup-${DATE_SUFFIX}  --source-instance=vm-wh04 --source-instance-zone=${LOCATION}

gcloud compute machine-images create vm-wh91-backup-${DATE_SUFFIX}  --source-instance=vm-wh91 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh92-backup-${DATE_SUFFIX}  --source-instance=vm-wh92 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh93-backup-${DATE_SUFFIX}  --source-instance=vm-wh93 --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-wh94-backup-${DATE_SUFFIX}  --source-instance=vm-wh94 --source-instance-zone=${LOCATION}

gcloud compute machine-images create vm-main-backup-${DATE_SUFFIX}  --source-instance=vm-main --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-loader-backup-${DATE_SUFFIX}  --source-instance=vm-loader --source-instance-zone=${LOCATION}
gcloud compute machine-images create vm-loader2-backup-${DATE_SUFFIX}  --source-instance=vm-loader2 --source-instance-zone=${LOCATION}


set +x
# Debug mode - off
echo "Running the script,.. completed!"
