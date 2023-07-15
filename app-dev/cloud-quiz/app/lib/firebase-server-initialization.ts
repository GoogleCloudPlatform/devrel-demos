import { initializeApp, getApps, App } from 'firebase-admin/app';
import { firebaseConfig } from "@/app/lib/firebase-config";

export let app: App;

if (getApps().length < 1) {
    app = initializeApp(firebaseConfig);
}