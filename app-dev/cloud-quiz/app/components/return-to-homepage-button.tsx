"use client"
import { useRouter } from 'next/navigation'


import "./big-color-border-button.css";

export default function ReturnToHomepageButton() {
  const router = useRouter()
  const onReturnToHomepageClick = async() => {
    router.push('/')
  }

  return (
    <button onClick={onReturnToHomepageClick} className={`color-border draw`}>Return to Homepage</button>
  )
}
