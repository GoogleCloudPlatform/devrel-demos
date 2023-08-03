"use client"
import { signInAnonymously } from "firebase/auth";
import { auth } from "@/app/lib/firebase-client-initialization";
import BigColorBorderButton from "./big-color-border-button";

export default function SignInButton() {
  const onSignInClick = async () => {
    signInAnonymously(auth);
  }

  return (
    <button onClick={onSignInClick} className={`text-gray-700 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black block rounded-md px-3 py-2 text-base font-medium`}>
      Sign In
    </button>
  )
}
