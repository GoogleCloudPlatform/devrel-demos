"use client"
import { Auth, signOut } from "firebase/auth";

export default function SignOutButton({ auth }: { auth: Auth }) {
  const onSignOutClick = (): void => {
    signOut(auth).then(() => {
      // Sign-out successful.
    }).catch((error) => {
      // An error happened.
    });
  }

  return (
    <button onClick={onSignOutClick}>Sign Out</button>
  )
}
