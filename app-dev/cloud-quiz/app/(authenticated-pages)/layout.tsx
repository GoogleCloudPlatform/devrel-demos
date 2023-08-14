"use client"

import '@/app/globals.css';
import Image from 'next/image';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import BigSignInButton from '@/app/components/big-sign-in-button';
import Navbar from '@/app/components/navbar';

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
          <>
            <Navbar />
            <center className='pt-20'>
              <div className='h-20'>
                <Image
                  src='/google-cloud-logo.svg'
                  alt='Google Cloud Logo'
                  width={0}
                  height={0}
                  sizes="100vw"
                  style={{ width: '100%', height: '100%' }} // optional
                  priority
                />
              </div>
              <h1 className='text-4xl pt-10'>Party Game</h1>
              <h2 className='pb-10'>Test your knowledge of Google Cloud.</h2>
              <BigSignInButton />
            </center>
          </>)}
      </div>
    </main>
  )
}
