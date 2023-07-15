"use client"

// Import the functions you need from the SDKs you need
import { db } from "@/app/lib/firebase-client-initialization";
import { onSnapshot, doc, DocumentReference } from "firebase/firestore";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import SignOutButton from "@/app/components/sign-out-button";
import SignInButton from "@/app/components/sign-in-button";
import CreateGameButton from "@/app/components/create-game-button";
import { Game, emptyGame, gameStates } from "@/app/types";
import Lobby from "@/app/components/lobby";
import GameList from "@/app/components/gameList";
import QuestionPanel from "@/app/components/question-panel";

async function getData() {
  const res = await fetch('/api/hello');
  // The return value is *not* serialized
  // You can return Date, Map, Set, etc.

  // Recommendation: handle errors
  if (!res.ok) {
    // This will activate the closest `error.js` Error Boundary
    throw new Error('Failed to fetch data')
  }

  return res;
}


async function addSomethingToAPIEndpoint(token: any) {
  console.log('adding to endpoint')

  const res = await fetch('/api/protected', {
    method: 'POST',
    body: JSON.stringify({ text: 'this is great text content' }),
    headers: {
      Authorization: token,
    }
  });
  // The return value is *not* serialized
  // You can return Date, Map, Set, etc.

  // Recommendation: handle errors
  if (!res.ok) {
    // This will activate the closest `error.js` Error Boundary
    throw new Error('Failed to fetch data')
  }

  return res;
}

export default function Home() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const [data, setData] = useState<any>({});
  const [token, setToken] = useState<any>({});
  const authUser = useFirebaseAuthentication();

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestion = game.questions[game.currentQuestionIndex];

  useEffect(() => {
    if (authUser.uid) {
      // declare the data fetching function
      const fetchData = async () => {
        const data = await getData()
        setData(data);
      }

      const postData = async () => {
        const token = await authUser.getIdToken();
        console.log(token);
        setToken(token);
        const data = await addSomethingToAPIEndpoint(token)
        setData(data);
      }



      // call the function
      fetchData()
        .then(postData)
        // make sure to catch any error
        .catch(console.error);
    }
  }, [authUser.uid])

  useEffect(() => {
    if (gameRef?.id) {
      const unsubscribe = onSnapshot(doc(db, "games", gameRef.id), (doc) => {
        const game = doc.data() as Game;
        setGame(game);
      });
      return unsubscribe;
    } else {
      setGame(emptyGame);
    }
  }, [gameRef])

  useEffect(() => {
    if (!authUser.uid) {
      setGameRef(undefined);
    }
  }, [authUser.uid])

  return (
    <main className="p-24 flex justify-between container mx-auto">
      <div>
        {authUser.uid ? (<>
          {(game.state === gameStates.GAME_OVER) && <div>
            {gameStates.GAME_OVER}
          </div>}
          {(!gameRef || game.state === gameStates.GAME_OVER) && <div>
            <CreateGameButton setGameRef={setGameRef} />
            <GameList setGameRef={setGameRef} />
          </div>}
          {showingQuestion && gameRef && (<>
            <QuestionPanel game={game} gameRef={gameRef} currentQuestion={currentQuestion} />
          </>)}
          {game.state === gameStates.NOT_STARTED && gameRef && (
            <Lobby gameRef={gameRef} setGameRef={setGameRef} />
          )}
          <br />
          <SignOutButton />
        </>) : (<>
          <SignInButton />
        </>)}
        <pre>
          {JSON.stringify({ data, token, authUser: authUser?.uid || '' })}
        </pre>
      </div>
      {/* TODO: Remove this pre tag, just here do make debugging faster */}
      {/* <pre>
        {JSON.stringify({
          authUser: {
            uid: authUser.uid,
            displayName: authUser.displayName,
          },
          game: {
            gameRefId: gameRef?.id,
            state: game.state,
            players: game.players,
            leader: game.leader,
          }
        }, null, 2)}
      </pre> */}
    </main>
  )
}
