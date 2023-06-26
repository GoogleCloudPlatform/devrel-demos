import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyBr0i2bC9kdsdRVh-9pQ5yFOjxpweiTJrQ",
  authDomain: "cloud-quiz-next.firebaseapp.com",
  projectId: "cloud-quiz-next",
  storageBucket: "cloud-quiz-next.appspot.com",
  messagingSenderId: "406096902405",
  appId: "1:406096902405:web:7311c44c3657568af1df6c",
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);