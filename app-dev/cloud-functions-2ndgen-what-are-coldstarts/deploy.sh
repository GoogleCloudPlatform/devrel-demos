YOUR_FUNCTION_NAME=what-are-cold-starts
YOUR_REGION=us-central1
YOUR_RUNTIME=nodejs16
YOUR_SOURCE_LOCATION=.
YOUR_CODE_ENTRYPOINT=cold-starts
TRIGGER_FLAGS="--trigger-http --allow-unauthenticated"

gcloud functions deploy $YOUR_FUNCTION_NAME \
--gen2 \
--region=$YOUR_REGION \
--runtime=$YOUR_RUNTIME \
--source=$YOUR_SOURCE_LOCATION \
--entry-point=$YOUR_CODE_ENTRYPOINT \
$TRIGGER_FLAGS