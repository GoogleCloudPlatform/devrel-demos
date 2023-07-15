"use client"
import { db } from "@/app/lib/firebase-client-initialization";
import { DocumentData, DocumentReference, QuerySnapshot, addDoc, collection, getDocs, serverTimestamp } from "firebase/firestore";
import { gameStates } from "@/app/types";
import { Dispatch, SetStateAction } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function CreateGameButton({ setGameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {
  const authUser = useFirebaseAuthentication();
  const onCreateGameClick = async () => {
    const token = await authUser.getIdToken();
    const res = await fetch('/api/create-game', {
      method: 'POST',
      body: JSON.stringify({ text: 'this is great text content' }),
      headers: {
        Authorization: token,
      }
    }).then(async (response) => {
      const ressy = await response.json();
      console.log({ response: ressy });
      setGameRef(ressy);
    }).catch(error => {
      console.log({ error })
    });
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20 p-2`}>Create a New Game</button>
  )
}
