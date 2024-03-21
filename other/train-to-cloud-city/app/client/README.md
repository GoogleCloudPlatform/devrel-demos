# ☁️🚂 Cloud Train Client

Calling all Cloud builders! Explore GCP Cloud City by helping us put together the Cloud Train.
You will need to follow the schematics and order the GCP resource train cars just so, or else the train will never complete its route!

## Getting started

1. Create a new project within [Firebase](https://console.firebase.google.com/).

2. Populate a local environment variables file (`.env`) with the following to initialize Firebase.
   You can retrieve these
   values from the project settings of the Firebase dashboard.

```bash
REACT_APP_FIREBASE_API_KEY=<firebase-api-key>
REACT_APP_FIREBASE_AUTH_DOMAIN=<firebase-auth-domain>
REACT_APP_GCP_PROJECT_ID=<firebase-gcp-project-id>
REACT_APP_FIREBASE_STORAGE_BUCKET=<firebase-storage-bucket>
REACT_APP_FIREBASE_MESSAGING_SENDER_ID=<firebase-messaging-sender-id>
REACT_APP_FIREBASE_APP_ID=<firebase-app-id>
REACT_APP_FIREBASE_MEASUREMENT_ID=<firebase-measurement-id>
```

3. Install npm dependencies and start up the client app.

```bash
npm install 
npm run build
npm start
```
Your browser should open up to `localhost:3000`.
