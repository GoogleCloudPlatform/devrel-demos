# make sure the Functions identity has Editor access to your sheet
export SHEET_ID=<YOUR_SHEET_ID>

gcloud functions deploy post-temperature --gen2 --region=us-central1 --runtime=nodejs16 --entry-point=post-temperature --trigger-http --allow-unauthenticated --set-env-vars SHEET_ID=$SHEET_ID --source="./post-temperature" &
gcloud functions deploy write-bigquery --gen2 --region=us-central1 --runtime nodejs16 --entry-point=write-bigquery --trigger-topic readings --no-allow-unauthenticated --retry --set-env-vars SHEET_ID=$SHEET_ID --source="./write-bigquery" &
gcloud functions deploy write-firestore --gen2 --region=us-central1 --runtime nodejs16 --entry-point=write-firestore --trigger-topic readings --no-allow-unauthenticated --retry --set-env-vars SHEET_ID=$SHEET_ID --source="./write-firestore"
