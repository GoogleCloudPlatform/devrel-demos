#!/bin/bash

export GOOGLE_APPLICATION_CREDENTIALS=/home/google/.keys/key.json
export PROJECT_ID=${1}
cd /home/google/devrel-demos/data-analytics/data-dash/pi
git pull https://github.com/GoogleCloudPlatform/devrel-demos.git
. sensors/bin/activate 
python rfid.py >> /home/google/xyz.txt 2>&1 &