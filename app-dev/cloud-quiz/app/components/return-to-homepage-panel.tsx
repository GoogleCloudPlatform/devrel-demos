"use client"

import Image from 'next/image';
import BigColorBorderButton from '@/app/components/big-color-border-button';
import { useRouter } from 'next/navigation'


export default function ReturnToHomepagePanel({ children }: { children: React.ReactNode }) {

  const router = useRouter()
  return (
    <div>
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
        {children}
        <BigColorBorderButton onClick={() => router.push('/')}>
          Return to Homepage
        </BigColorBorderButton>
      </center>
    </div>
  )
}
