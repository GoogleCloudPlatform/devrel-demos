"use client"

import { DocumentReference } from "firebase/firestore";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { useRouter } from 'next/navigation'

export default function DeleteGameButton({ gameRef }: { gameRef: DocumentReference }) {
  const authUser = useFirebaseAuthentication();
  const router = useRouter()

  const onDeleteGameClick = async (gameRef: DocumentReference) => {
    const token = await authUser.getIdToken();
    await fetch('/api/delete-game', {
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
      <button onClick={() => onDeleteGameClick(gameRef)} className={`border mt-20`}>Delete Game</button>
    </div>
  )
}
