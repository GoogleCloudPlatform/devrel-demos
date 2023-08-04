"use client"
import { signInAnonymously } from "firebase/auth";
import { auth } from "@/app/lib/firebase-client-initialization";

import "@/app/components/big-color-border-button.css";

export default function BigSignInButton() {
  const onSignInClick = async() => {
    signInAnonymously(auth);
  }

  return (
    <button onClick={onSignInClick} className={`color-border draw`}>Sign In Anonymously</button>
  )
}
