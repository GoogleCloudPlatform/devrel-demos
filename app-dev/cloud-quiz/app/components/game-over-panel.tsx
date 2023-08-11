"use client"

import Image from 'next/image';
import ReturnToHomepageButton from '@/app/components/return-to-homepage-button';

export default function GameOverPanel() {
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
        <h2>Game Over</h2>
        <ReturnToHomepageButton />
      </center>
    </div>
  )
}
