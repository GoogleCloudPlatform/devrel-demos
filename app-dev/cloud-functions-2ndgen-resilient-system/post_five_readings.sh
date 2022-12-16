FUNCTION_URL="$(gcloud functions describe post-temperature --gen2 --region us-central1 --format='get(serviceConfig.uri)')"
a=1

while [ $a -lt 6 ]
do
  sleep 1
  echo "Making HTTP post $a to post-temperature()"

  curl -H "Content-Type:application/json" \
    -X POST \
    -d "{\"sensor_id\":$(((RANDOM%900)+99)), \"temperature\":$(((RANDOM%110)+30)), \"source\":\"IoT\"}" \
    $FUNCTION_URL
      
  a=`expr $a + 1`
done
