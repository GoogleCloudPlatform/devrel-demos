"use client"
import { db, auth } from "@/app/lib/firebase-initialization";
import { QuerySnapshot, addDoc, collection, getDocs } from "firebase/firestore";
import { gameStates } from "@/app/types";

export default function CreateGameButton({ setGameRef }: { setGameRef: Function }) {
  const onCreateGameClick = async () => {
    const querySnapshot: QuerySnapshot = await getDocs(collection(db, "questions"));
    const questions = querySnapshot.docs.reduce((agg, doc, index) => {
      return { ...agg, [index]: doc.data() }
    }, {});
    if (!auth.currentUser) throw new Error('User must be signed in to start game');
    const leader = {
      displayName: auth.currentUser.displayName || '',
      uid: auth.currentUser.uid || '',
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
    });
    setGameRef(gameRef);
  }

  return (
    <button onClick={onCreateGameClick} className={`border mt-20`}>Create a New Game</button>
  )
}
