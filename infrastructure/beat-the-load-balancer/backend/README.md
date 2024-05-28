
## How to deploy Applications

Check the README.md in `/infra` folder to do the necessary infrastructure.

As of Feb 6th, 2024 the infrastructure is deployed to https://console.cloud.google.com/welcome?project=beat-the-load-balancer

Once the infra setup is completed used the `makefile` to set up the Applications

use `make help` to more details.

#### About Applications

* Loader/Locust is the application for sending messages
* User-Gui App is the simulator for User App(used for Testing)
* Warehouse is the application for processing messages


## Step to install & run an app

### Copy /app to Cloud VM

* Use make's `deploy` commands to copy `/app` files to a cloud VMs.

### Setup Gunicorn

Learn more @ https://flask.palletsprojects.com/en/2.3.x/deploying/gunicorn/

* Pkg Install

```
alias python=python3
alias pip=pip3
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install python3-pip -y
sudo apt-get install python3-venv -y
```

* Setup virtual env & g-Unicorn

# /home/sampathm/load-balancing-blitz/venv/bin/python
```
cd /home/sampathm/app
python3 -m venv venv
. .venv/bin/activate
pip install -r requirements.txt
```

* (Optional) A firewall allow test: Run following and try to access it via external IP

```
python3 -m http.server -b 0.0.0.0 8080
```

* Testing flask app: use following command to test you app is working fine.
```
flask --app user_app run --port 8080 --host 0.0.0.0
flask --app loader run --port 8080 --host 0.0.0.0
flask --app warehouse run --port 8080 --host 0.0.0.0
```

machine specific command
```
flask --app game:flaskapp run --port 8080 --host 0.0.0.0
```

* (optional) Testing app with g-unicorn

```
which gunicorn
gunicorn --bind 0.0.0.0:8080 game:flaskapp
```

* Testing app with g-unicorn(outside virtual env)
```
# exit from virtual env
deactivate 
# run flask application gUnicorn from virtual env
/home/sampathm/app/.venv/bin/gunicorn --bind 0.0.0.0:8080 game:flaskapp

#/home/sampathm/load-balancing-blitz/venv/bin/gunicorn  --bind 0.0.0.0:8080 game:flaskapp
```

## Nginx Setup & Test

* To install nginx

```
# install nginx
sudo apt-get install nginx -y
```

Use VM's Eternal IP at port `80` and access

The default config is at `/etc/nginx/sites-available/default`


* To check if nginx is running

```commandline
sudo systemctl status nginx
```


## Nginx configuration & service file
```
sudo cat nginx_config/flaskapp.conf > /etc/nginx/sites-available/flaskapp
sudo cat nginx_config/flaskapp.service /etc/systemd/system/flaskapp.service
```

* Create Symbolic link in enabled sites

```
cd /etc/nginx/sites-enabled

sudo ln -s /etc/nginx/sites-available/flaskapp
```

* Create nginx - gUnicorn service
```
 
```

Add file content
```
[Unit]
Description=Gunicorn instance to serve flaskapp
After=network.target
[Service]
User=sampathm
Group=sampathm
WorkingDirectory=/home/sampathm/app
Environment="PATH=/home/sampathm/app/.venv/bin"
ExecStart=/home/sampathm/app/.venv/bin/gunicorn --bind 0.0.0.0:5000 game:flaskapp

[Install]
WantedBy=multi-user.target
```

* Run following command to check `flaskapp` status & start the nginx service for your application

```
sudo systemctl status flaskapp
sudo systemctl start flaskapp
```

* command for debugging
```
sudo systemctl stop flaskapp
sudo systemctl start flaskapp
sudo systemctl restart flaskapp
```

* command for debugging
```
sudo journalctl -u flaskapp.service 
sudo journalctl -u nginx.service 
```

## maintenance

* command status services

```
systemctl is-active flaskapp nginx
```

For more detailed answer!

```
sudo systemctl status flaskapp
sudo systemctl status nginx
```


* command stop services
```
sudo systemctl stop flaskapp
sudo systemctl stop nginx
```

* command start services
```
sudo systemctl start nginx
sudo systemctl start flaskapp
```

* command re-start services
```
sudo systemctl restart flaskapp
sudo systemctl restart nginx
```

# Reference

Tutorial on Nginx
* https://phoenixnap.com/kb/nginx-start-stop-restart
* https://phoenixnap.com/kb/nginx-start-stop-restart
* https://phoenixnap.com/kb/nginx-start-stop-restart


Python
* https://realpython.com/python-http-server/
* python3 -m http.server 8080
* python3 -m http.server -b 0.0.0.0 8080


Reference
* https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-18-04
* https://flask.palletsprojects.com/en/3.0.x/deploying/nginx/
* 


Compute VM

* Below command is for creating `vm-wh02` vm, from a machine image `vm-main-9-feb-2024`
```bash
gcloud compute instances create vm-wh02 \
    --project=beat-the-load-balancer \
    --zone=us-central1-a \
    --description=created\ \
from\ an\ instance\ template \
    --machine-type=n1-standard-1 \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --can-ip-forward \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=991433935243-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/trace.append \
    --min-cpu-platform=Automatic \
    --tags=game,web-server \
    --no-shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=goog-ec-src=vm_add-gcloud \
    --reservation-affinity=any \
    --source-machine-image=vm-main-9-feb-2024
```



```bash
cd app
rm *
rm -rf pubsub/ templates/
```

From local machine deployed code to all machines


```
cat /etc/systemd/system/flaskapp.service | grep game:flaskapp
```

```bash
source .venv/bin/activate

pip install -r requirements.txt

flask --app game:flaskapp run --port 8000 --host 0.0.0.0
```


# Todo / to fix

* (p1) Sending messages to PubSub from Compute VM (Code is ready but having issue when from cloud VM)
* (p1) In Loader - Collecting statistics from BigQuery & respond to API Calls
* setup a LB


To restart a cron job

```bash

sudo service cron reload

```