"use client"
import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { auth } from "@/app/lib/firebase-initialization";

export default function SignInButton() {
  const provider = new GoogleAuthProvider();

  const onSignInClick = async() => {
    signInWithPopup(auth, provider);
  }

  return (
    <button onClick={onSignInClick} className={`border mt-20`}>Sign In with Google</button>
  )
}
