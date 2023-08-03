"use client"

import { DocumentReference } from "firebase/firestore";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import "./big-color-border-button.css";
import BigColorBorderButton from "@/app/components/big-color-border-button";

export default function StartGameButton({gameRef}: {gameRef: DocumentReference}) {
  const authUser = useFirebaseAuthentication();
  const onStartGameClick = async (gameRef: DocumentReference) => {
    const token = await authUser.getIdToken();
    await fetch('/api/start-game', {
      method: 'POST',
      body: JSON.stringify({ gameId: gameRef.id }),
      headers: {
        Authorization: token,
      }
    })
    .catch(error => {
      console.error({ error })
    });
  }

  return (
    <BigColorBorderButton onClick={() => onStartGameClick(gameRef)}>
      Start Game Now ►
    </BigColorBorderButton>
  )
}
