## Applications

The backend compute infra for BLB is distributed into 3 applications that work independently.

* Loader application is for generating and sending HTTP traffic
* User Application is the front for receiving HTTP traffic from Loader and 
  distributing it according to user inputs. 
* Worker application is processing received HTTP traffic and generates score

## How to setup?

(Optional) If you want to have a dedicated folder

    mkdir app
    cd app
    # (optional)
    # sudo apt-get install git python3-pip python3.11-venv -y

clone the repository

    git clone https://github.com/GoogleCloudPlatform/devrel-demos.git
    cd devrel-demos/infrastructure/beat-the-load-balancer/backend

(Optional) If you need to install `pip`

    python3 -m venv venv
    source venv/bin/activate

Install requirements and running application in demo mode.

    pip install -r requirements.txt

    


gcloud artifacts repositories create quickstart-docker-repo --repository-format=docker \
  --location=us-west2 --description="Docker repository" --project=beat-the-load-balancer

gcloud builds submit --region=us-west2 --tag us-west2-docker.pkg.dev/beat-the-load-balancer/quickstart-docker-repo/quickstart-image:tag1  --project=beat-the-load-balancer