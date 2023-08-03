"use client"
import { useRouter } from 'next/navigation'
import BigColorBorderButton from './big-color-border-button'

export default function ReturnToHomepageButton() {
  const router = useRouter()

  return (
    <BigColorBorderButton onClick={() => router.push('/')}>
      Return to Homepage
    </BigColorBorderButton>
  )
}
