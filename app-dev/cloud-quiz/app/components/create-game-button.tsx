"use client"

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { useRouter } from 'next/navigation'

export default function CreateGameButton() {
  const authUser = useFirebaseAuthentication();
  const router = useRouter()
  const onCreateGameClick = async () => {
    const token = await authUser.getIdToken();
    const response = await fetch('/api/create-game', {
      method: 'POST',
      headers: {
        Authorization: token,
      }
    })
    .then(res => res.json())
    .catch(error => {
      console.error({ error })
    });

    router.push(`/game/${response.gameId}`)
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20 p-2`}>Create a New Game</button>
  )
}
