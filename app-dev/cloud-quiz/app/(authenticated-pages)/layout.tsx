"use client"

import '@/app/globals.css'
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import SignInButton from '@/app/components/sign-in-button';
import SignOutButton from '@/app/components/sign-out-button';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const authUser = useFirebaseAuthentication();

  return (
    <main className="p-24 flex justify-between container mx-auto">
      <div>
        {authUser.uid ? (
          <>
            {children}
            <br />
            <SignOutButton />
          </>
        ) : (
          <SignInButton />
        )}
      </div>
    </main>
  )
}
