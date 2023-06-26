"use client"
import { signOut } from "firebase/auth";
import { auth } from "@/app/lib/firebase-initialization";

export default function SignOutButton() {
  const onSignOutClick = (): void => {
    signOut(auth).then(() => {
      // Sign-out successful.
    }).catch((error) => {
      // An error happened.
    });
  }

  return (
    <button onClick={onSignOutClick} className={`border mt-20`}>Sign Out</button>
  )
}
