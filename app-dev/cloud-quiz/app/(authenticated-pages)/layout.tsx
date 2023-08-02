"use client"

import '@/app/globals.css';
import Image from 'next/image';
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
          <center className='pt-20'>
            <div className='h-20'>
              <Image
                src='/google-cloud-logo.svg'
                alt='Google Cloud Logo'
                width={0}
                height={0}
                sizes="100vw"
                style={{ width: '100%', height: '100%' }} // optional            
              />
            </div>
            <h1 className='text-4xl pt-10'>Cloud Quiz</h1>
            <h2 className='pb-10'>Test your knowledge of Google Cloud.</h2>
            <SignInButton />
          </center>
        )}
      </div>
    </main>
  )
}
