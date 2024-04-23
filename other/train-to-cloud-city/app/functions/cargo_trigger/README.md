


```sh
pip3 install -r requirements.txt


gcloud functions deploy cargo_trigger \
--project train-to-cloud-city-4 \
--gen2 \
--region=us-west4 \
--trigger-location=us-west4 \
--runtime=python310 \
--source=. \
--entry-point=cargo_trigger \
--trigger-event-filters="type=google.cloud.firestore.document.v1.updated" \
--trigger-event-filters="database=(default)" \
--trigger-event-filters-path-pattern="document=global*/cargo" \
```