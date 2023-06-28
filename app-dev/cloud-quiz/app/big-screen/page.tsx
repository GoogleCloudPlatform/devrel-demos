"use client"

// Import the functions you need from the SDKs you need
import { db } from "@/app/lib/firebase-initialization";
import { onSnapshot, doc, DocumentReference, updateDoc } from "firebase/firestore";
import { useEffect, useState } from 'react';
import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import SignOutButton from "@/app/components/sign-out-button";
import SignInButton from "@/app/components/sign-in-button";
import CreateGameButton from "@/app/components/create-game-button";
import { Game, emptyGame, gameStates } from "@/app/types";
import Lobby from "@/app/components/lobby";
import GameList from "@/app/components/gameList";
import QuestionPanel from "@/app/components/question-panel";
import Link from "next/link";


export default function Home() {
  const [gameRef, setGameRef] = useState<DocumentReference>();
  const [game, setGame] = useState<Game>(emptyGame);
  const authUser = useFirebaseAuthentication();

  const showingQuestion = game.state === gameStates.AWAITING_PLAYER_ANSWERS || game.state === gameStates.SHOWING_CORRECT_ANSWERS;
  const currentQuestion = game.questions[game.currentQuestionIndex];

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
// co
  useEffect(() => {
    if (!authUser.uid) {
      setGameRef(undefined);
    }
  }, [authUser.uid])

  return (
    <main className="p-24 flex justify-between space-x-24">
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
          <Link href="/" className="underline text-blue-600">Join the fun!</Link>
        </>)}
      </div>
      {/* TODO: Remove this pre tag, just here do make debugging faster */}
      <pre>
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
      </pre>
    </main>
  )
}
