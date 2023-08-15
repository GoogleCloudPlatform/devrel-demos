/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

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
