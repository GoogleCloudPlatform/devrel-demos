import { initializeApp, getApps, App } from 'firebase-admin/app';
import { firebaseConfig } from "@/app/lib/firebase-config";
const { getFirestore } = require('firebase-admin/firestore');

export let app: App;
export let db: any;

if (getApps().length < 1) {
  app = initializeApp(firebaseConfig);
  db = getFirestore();
}
