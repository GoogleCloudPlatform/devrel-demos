#!/bin/bash

# This is a QuickHack.
# This is a cleanup/code update in gcloud compute instances

echo "running the script"
sleep 0.3
set -x

echo "deactivate - may fail"
sleep 0.1
deactivate

echo "activate virtualenv"
sleep 0.3
source /home/sampathm/load-balancing-blitz/venv/bin/activate

echo "update repo"
sleep 0.3
cd /home/sampathm/load-balancing-blitz/app
git pull -a

set +x
echo "done!"