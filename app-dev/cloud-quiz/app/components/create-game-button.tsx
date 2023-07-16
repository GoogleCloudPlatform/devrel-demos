"use client"
import { db } from "@/app/lib/firebase-client-initialization";
import { DocumentData, DocumentReference, doc } from "firebase/firestore";
import { Dispatch, SetStateAction } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function CreateGameButton({ setGameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {
  const authUser = useFirebaseAuthentication();
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
      console.log({ error })
    });

    const gameRef = doc(db, 'games', response.gameId);

    setGameRef(gameRef);
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20 p-2`}>Create a New Game</button>
  )
}
