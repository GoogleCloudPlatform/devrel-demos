This is not an officially supported Google product. This project is not
eligible for the [Google Open Source Software Vulnerability Rewards
Program](https://bughunters.google.com/open-source-security).

This project is intended for demonstration purposes only. It is not
intended for use in a production environment.

You can review [Google Cloud terms of service
here](https://console.cloud.google.com/tos?id=cloud).

To run this demo, start by creating a [Google Managed Service for Apache Kafka](https://cloud.google.com/managed-service-for-apache-kafka/docs/setup-kafka). 

Then ensure the properties for Kafka and JAVA are set. 

Set your PROJECT_ID environment variable and execute run_compute_engine_client.sh 


```
export PROJECT_ID=<YOUR PROJECT ID GOES HERE>
sh run_compute_engine_client.sh
```
The default cluster name is kafka-test and the default topic is test_topic. 
These can be found in kafka-client.properties. 

To update the properties, uncomment the line and re-run the run_compute_engine_client.sh script. 

bootstrap.servers=bootstrap.kafka-test.us-central1.managedkafka.{$PROJECT}.cloud.goog:9092
topic=test_topic