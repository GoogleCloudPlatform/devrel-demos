"use client"
import { signOut } from "firebase/auth";
import { auth } from "@/app/lib/firebase-client-initialization";

export default function SignOutButton() {
  const onSignOutClick = (): void => {
    signOut(auth);
  }

  return (
    <button onClick={onSignOutClick} className={`text-gray-700 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black block rounded-md px-3 py-2 text-base font-medium`}>
      Sign Out
    </button>
  )
}
