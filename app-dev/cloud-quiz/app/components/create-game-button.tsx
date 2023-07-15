"use client"
import { db } from "@/app/lib/firebase-client-initialization";
import { DocumentData, DocumentReference, QuerySnapshot, addDoc, collection, getDocs, serverTimestamp } from "firebase/firestore";
import { gameStates } from "@/app/types";
import { Dispatch, SetStateAction } from "react";
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";

export default function CreateGameButton({ setGameRef }: { setGameRef: Dispatch<SetStateAction<DocumentReference<DocumentData> | undefined>> }) {
  const authUser = useFirebaseAuthentication();
  const onCreateGameClick = async () => {
    const querySnapshot: QuerySnapshot = await getDocs(collection(db, "questions"));
    const questions = querySnapshot.docs.reduce((agg, doc, index) => {
      return { ...agg, [index]: doc.data() }
    }, {});
    if (!authUser) throw new Error('User must be signed in to start game');
    const leader = {
      displayName: authUser.displayName || '',
      uid: authUser.uid || '',
    };

    const gameRef = await addDoc(collection(db, "games"), {
      questions,
      leader,
      // TODO: Remove leader from game players, this just makes testing faster
      players: {
        [leader.uid]: leader.displayName, 
      },
      state: gameStates.NOT_STARTED,
      currentQuestionIndex: 0,
      startTime: serverTimestamp(),
      timePerQuestion: 30,
      timePerAnswer: 10,
    });
    setGameRef(gameRef);
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20 p-2`}>Create a New Game</button>
  )
}
