"use client"

import { DocumentReference } from "firebase/firestore";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { useRouter } from 'next/navigation'

export default function ExitGameButton({ gameRef }: { gameRef: DocumentReference }) {
  const authUser = useFirebaseAuthentication();
  const router = useRouter()

  const onExitGameClick = async (gameRef: DocumentReference) => {
    const token = await authUser.getIdToken();
    await fetch('/api/exit-game', {
      method: 'POST',
      body: JSON.stringify({ gameId: gameRef.id }),
      headers: {
        Authorization: token,
      }
    }).then(() => router.push('/'))
    .catch(error => {
      console.error({ error })
    });
  }

  return (
    <div>
      <button onClick={() => onExitGameClick(gameRef)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
