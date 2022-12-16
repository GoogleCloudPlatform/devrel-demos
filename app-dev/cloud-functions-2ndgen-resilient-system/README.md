# Cloud Functions resiliency demo

## Project setup

### Set your Google Cloud Project.

```console
gcloud config set project <YOUR_PROJECT_ID>
```

### Enable the Sheets and Cloud Functions APIs.

```console
gcloud services enable sheets.googleapis.com cloudfunctions.googleapis.com
```

### Create Firestore instance

1. [Create Firestore database](https://console.cloud.google.com/firestore/) in Native Mode, and choose the same region as you'll deploy your functions (e.g. us-east1).

### Create a tracking sheet in Google Sheets.

1. Create a new Google Sheets document - copy [this example spreadsheet](https://docs.google.com/spreadsheets/d/17kFEUvQHtYBg-jxjWXPDOlQe4XiaJy0zzVboKoZcQW0/edit?usp=sharing)
2. Share with the Functions identity service account (e.g. <YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com>)

### Add your SHEET_ID in the Functions deployment script

You can get the Google Sheets ID from the URL of your spreadsheet. If the URL is https://docs.google.com/spreadsheets/d/17kFEUvQHtYBg-jxjWXPDOlQe4XiaJy0zzVboKoZcQW0 then the SHEET_ID is `17kFEUvQHtYBg-jxjWXPDOlQe4XiaJy0zzVboKoZcQW0`.

### Create PubSub topics

```console
gcloud pubsub topics create readings
```

### Create BigQuery dataset and table.

```console
bq --location=us-east1 mk \
    --dataset \
    --description "Sensor data for IoT data (GCF resiliency demo)." \
    sensor_data
```

```console
bq query --use_legacy_sql=false '
 CREATE TABLE sensor_data.readings (
    sensor_id   INT64     NOT NULL  OPTIONS(description="Sensor identifier"),
    temperature NUMERIC   NOT NULL  OPTIONS(description="Temperature in degrees Fahrenheit"),
    source      STRING              OPTIONS(description="Geographic source of the sensor"),
    ts          INT64   NOT NULL    OPTIONS(description="Timestamp of the sensor reading")
    ) OPTIONS (
      description="Sensor reading data for GCF resiliency demo."
    )'
```

The table will be in the format:

```
sensor_id   INTEGER REQUIRED
temperature NUMERIC REQUIRED
source      STRING  NULLABLE
ts          INTEGER REQUIRED
```

### Deploy the Cloud Functions.

```console
./deploy_all_functions.sh
```

### Simulate incoming IoT sensor data

With the sheet opened, run the following script to simulate 5 IoT sensors sending data to the post-temperature endpoint.

```console
./post_five_readings.sh
```
