"use client"

import '@/app/globals.css'
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import SignInButton from '@/app/components/sign-in-button';

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const authUser = useFirebaseAuthentication();

  return (
    <main>
      <div>
        {authUser.uid ? (
          <>
            {children}
          </>
        ) : (
          <SignInButton />
        )}
      </div>
    </main>
  )
}
