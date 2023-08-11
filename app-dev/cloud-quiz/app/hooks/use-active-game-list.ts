import { useEffect, useState } from "react";
import { db } from "@/app/lib/firebase-client-initialization"
import { gameStates } from "@/app/types";
import { DocumentReference, collection, onSnapshot, query, where } from "firebase/firestore";


const useActiveGameList = () => {
  const [activeGameList, setActiveGameList] = useState<DocumentReference[]>([]);

  useEffect(() => {
    const q = query(collection(db, "games"), where("state", "!=", gameStates.GAME_OVER));
    const unsubscribe = onSnapshot(q, (querySnapshot) => {
      const games: DocumentReference[] = [];
      querySnapshot.forEach((doc) => {
        games.push(doc.ref);
      });
      setActiveGameList(games);
    });
    return unsubscribe;
  }, [])

  return { activeGameList }
}

export default useActiveGameList;