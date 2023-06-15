# How to run this Python pipeline

## Validate Python installation
Dataflow instructions on [running Python pipelines](https://cloud.google.com/dataflow/docs/quickstarts/create-pipeline-python) 
describe the following steps in details.
- Validate you have Python3 installed:
```shell
python --version
```
- Create a "venv" environment
```shell
python -m venv env
```
- Activate it
```shell
source env/bin/activate
```
- Install required dependencies
```shell
pip3 install google-cloud-pubsub==2.1.0
pip3 install google-cloud-bigquery-storage==2.13.2
pip3 install apache-beam[gcp]==2.39.0
```

## Start the pipeline
To run the pipeline locally:
````shell
python main.py --runner DirectRunner \
 --input_files nyc_green_taxi_trips.csv \
 --classpath ../build/libs/beam_workshop-0.0.1.jar
````

To run the pipeline using the Dataflow runner:
```shell
PROJECT_ID=$PROJECT_ID

python main.py \
  --runner=DataflowRunner \
  --project=$PROJECT_ID \
  --region=us-central1 \
  --job_name=print-external \
  --temp_location="gs://$PROJECT_ID-gcs/dataflow/temp" \
  --experiments=use_runner_v2 \
  --input_files gs://$PROJECT_ID/beam_workshop/nyc_green_taxi_trips.csv \
  --classpath $HOME/beam_workshop/build/libs/beam_workshop-0.0.1.jar
```

## Cleanup
Once you finish running the pipeline you should exit from the "venv" environment:
```shell
deactivate
```

## Dataflow Execution
You'll need to make sure to update the local-host parameters or update for Dataflow execution.
(See difference between main.py and part3.py)

## Write to BQ 
This requires you to build an uberjar (fatjar) using the shadow plugin. 