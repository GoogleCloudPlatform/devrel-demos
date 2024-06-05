#!/usr/bin/make -f
# Copyright 2024 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Learning Resources:
#       * https://makefiletutorial.com/
################################################################################
#### > Help Guide < ##
##
## ===>  Applications
##
help: ## Help Command
	clear
	@fgrep -h "##" $(MAKEFILE_LIST) | fgrep -v fgrep | sed -e 's/\\$$//' | sed -e 's/##//'

warehouse: ## To run the Warehouse VM's Message Receiver Application
	echo "Starting Warehouse VM Service:" && python warehouse.py

user_gui: ## To run the GUI Application for User
	echo "Starting Warehouse VM Service:" && python user_app.py

loader: ## To run the API Load tester tool
	echo "locust" && locust --users 100 --spawn-rate 10 --processes 2 -t 60s

# locust: # To run locust server
# 	echo "locust" && locust --web-host 0.0.0.0 --web-port 8080 -f lib/locustfile.py

##
## ===> Utilities
##

vmlist: ## To list all the running VM instances
	echo "Listing VMs:" && gcloud compute instances list --project "beat-the-load-balancer" # --zone "us-central1-a"

vmlogin: ## To loging to a running VM instances, use `make vmlogin vm=<vm_name>`
	echo "Logging to VM: $(vm)" && gcloud compute ssh $(vm) --zone "us-central1-a" --project "beat-the-load-balancer"

vmtunnel: ## To tunnel to a cloud VM instance on port 8000, use `make vmtunnel vm=<vm_name>`
	echo "Logging to VM: $(vm)" && gcloud compute ssh $(vm) --zone "us-central1-a" --project "beat-the-load-balancer"  -- -NL 8000:localhost:8000



# loader2: # To run API Load tester tool without CLI
# 	echo "locust" && locust --headless --users 100 --spawn-rate 10 --processes 2 -t 60s

lint: ## Linter for HTML and Python
	djlint templates/ --profile=django --reformat && black .

redis: ## clear python cache files
	gcloud compute ssh game-development-redis-proxy --zone=us-central1-a -- -N -L 6379:10.114.97.227:6379

# redis: # clear python cache files
#	redis-server

py3clean: ## clear python cache files
	python3 -Bc "for p in __import__('pathlib').Path('.').rglob('*.py[co]'): p.unlink()" && python3 -Bc "for p in __import__('pathlib').Path('.').rglob('__pycache__'): p.rmdir()"


clear_logs: ## clear python cache files
	rm -rf __pycache__/ .pytest_cache .ruff_cache .DS_Store && rm /tmp/flask*


cleanup: pycache py3clean ## cleanup
	clear

clear: lint cleanup ## run all clean up jobs and clear screen
	clear

# #
# # ===> To deploy code
# #
#
# deploy-all: cleanup deploy-vm-loader deploy-vm-main deploy-vm-wh01 deploy-vm-wh02 deploy-vm-wh03 deploy-vm-wh04 # # To copy code to all VMs
# 	echo "Deploying code to VMs"
#
# deploy-vm-loader: cleanup
# 	gcloud compute copy-files ../app vm-loader:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"
#
# deploy-vm-main: cleanup # # To copy app/ folder to VM Machine named - "vm-main"
# 	gcloud compute copy-files ../app vm-main:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"
#
# deploy-vm-wh01: cleanup
# 	gcloud compute copy-files ../app vm-wh01:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"
#
# deploy-vm-wh02: cleanup
# 	gcloud compute copy-files ../app vm-wh02:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"
#
# deploy-vm-wh03: cleanup
# 	gcloud compute copy-files ../app vm-wh03:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"
#
# deploy-vm-wh04: cleanup
# 	gcloud compute copy-files ../app vm-wh04:/home/sampathm --zone "us-central1-a" --project "beat-the-load-balancer"


##
## ===> App Commands
##

app_status: ## To check the status of the flask application
	sudo systemctl status nginx flaskapp --no-pager --lines=0

app_stop: ##  To stop the flask application
	sudo systemctl stop nginx flaskapp

app_start:  ##  To start the flask application
	sudo systemctl start nginx flaskapp

app_restart:  ## To restart the flask application
	sudo systemctl restart nginx flaskapp


##
# to stop the service
super_start: ## to stop the supervisor service
	supervisord


super_status: ## to check status of the supervisor service
	ps -ef | grep supervisord | grep -v grep


super_stop: ## to stop the supervisor service
	ps -ef | grep supervisord | grep -v grep | awk '{ print $2 }' | xargs kill -s SIGTERM


##
super_apps_start: ## to start the Celery & Health Check Background Apps/programs
	supervisorctl start all


super_apps_stop: ## to start the Celery & Health Check Background Apps/programs
	supervisorctl stop all && rm /tmp/flaskapp_*


super_apps_status: ## to check the status of Celery & Health Check Background Apps/programs
	supervisorctl status all

##
start_all: app_start super_apps_start ## for flaskapp, celery & hc
	echo "start all apps"


stop_all: app_stop super_apps_stop ## for flaskapp, celery & hc
	echo "stop all apps"


reset_all: stop_all clear_logs start_all  ## for flaskapp, celery & hc
	echo "reset all apps"


#
# # cleanup
# superd_stop2:
# 	ps -ef | grep supervisord | grep -v grep | awk '{ print $2 }' | xargs sudo kill -s SIGTERM
#
# # to stop the running service
# superd_stop3:
# 	ps -auxww | grep '/home/sampathm/app/.venv/bin/celery' | grep -v grep | awk '{print $2}' | xargs sudo kill -9
#
# superd_stop: superd_stop1 superd_stop2 superd_stop3 superd_check1 superd_check2
# 	echo "completed the job"
#
#
# superd_logs:
# 	tail -f /tmp/flask_app_celeryd.log
#
#
# celery_stop:
# 	ps -auxww | grep '/home/sampathm/app/.venv/bin/celery' | grep -v " grep " | awk '{print $2}' | xargs sudo kill -9
#

# ps -ef | grep supervisord | grep -v grep | awk '{ print $2 }' | xargs kill -s SIGTERM
# sudo systemctl stop supervisor
# ps -auxww | grep '/home/sampathm/app/.venv/bin/celery' | grep -v " grep " | awk '{print $2}' | xargs kill -9

# locust

# function super_stop () {
# sudo /etc/init.d/supervisor stop;
# ps -ef | grep supervisord | grep -v grep | awk '{ print $2 }' | xargs sudo kill -s SIGTERM
# ps -auxww | grep '/home/sampathm/app/.venv/bin/celery' | grep -v " grep " | awk '{print $2}' | xargs sudo kill -9
# }

# Monitoring Agent - https://cloud.google.com/monitoring/agent/monitoring/installation#install-latest-version
# curl -sSO https://dl.google.com/cloudagents/add-monitoring-agent-repo.sh
# sudo bash add-monitoring-agent-repo.sh --also-install

# ps -ef | grep "celery" | grep -v grep | awk '{ print $2 }' | xargs sudo kill -s SIGTERM
# sudo systemctl stop supervisor



##
## ===> Logs
##

logs_app: ## Logs for flask application
	tail -f /tmp/flaskapp_game.log

logs_nginx: ## cleanup
	tail -f /var/log/nginx/access.log

locust2:
	locust --headless --users 10 --spawn-rate 1 -t 10s -f lib/locustfile.py

flower:
	celery --broker=redis://localhost:6379/0 flower

purge:
	celery --config lib.celeryconfig -A lib.celery_task purge -f

#
#
# superd_check1:
# 	ps -eaf | grep '/home/sampathm/app/.venv/bin/celery' | grep -v grep
#
# superd_check2:
# 	ps -eaf | grep supervisor | grep -v grep
#
# superd_start:
# 	cd /home/sampathm/app && sudo /etc/init.d/supervisor start && supervisord && ps -eaf | grep celery | grep -v grep
#
#
# superd_stop_ps:
# 	ps -eaf | grep supervisor | grep venv | awk '{print $2}' | xargs kill -9
#
# ps -eaf | grep supervisor | grep venv | awk '{print $2}' | xargs kill -9
# ps -eaf | grep celery | grep venv | awk '{print $2}' | xargs kill -9
# ps -eaf | grep python | grep venv | awk '{print $2}' | xargs kill -9
################################################################################

## ==> docker build

VERSION=01

build: ## build docker image
	podman build --tag blb:${VERSION} --file ./Dockerfile

run:
	podman rm -f main-vm && podman run -d --hostname main-vm --name main-vm blb:${VERSION}

game:
	podman exec -it main-vm bash


