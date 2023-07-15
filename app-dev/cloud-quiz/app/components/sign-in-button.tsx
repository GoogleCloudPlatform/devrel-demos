"use client"
import { signInAnonymously } from "firebase/auth";
import { auth } from "@/app/lib/firebase-client-initialization";

export default function SignInButton() {
  const onSignInClick = async() => {
    signInAnonymously(auth);
  }

  return (
    <button onClick={onSignInClick} className={`border mt-20`}>Sign In Anonymously</button>
  )
}
