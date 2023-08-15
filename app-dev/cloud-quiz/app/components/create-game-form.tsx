/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

"use client"

import useFirebaseAuthentication from "@/app/hooks/use-firebase-authentication";
import { useRouter } from 'next/navigation'
import { useEffect, useState } from "react";
import BigColorBorderButton from "./big-color-border-button";
import { gameFormValidator } from "../lib/game-form-validator";

export default function CreateGameForm() {
  const authUser = useFirebaseAuthentication();
  const defaultTimePerQuestion = 60;
  const defaultTimePerAnswer = 20;
  const [timePerQuestion, setTimePerQuestion] = useState<number>(defaultTimePerQuestion);
  const [timePerAnswer, setTimePerAnswer] = useState<number>(defaultTimePerAnswer);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const router = useRouter()
  const onCreateGameSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const token = await authUser.getIdToken();
    try {
      const res = await fetch('/api/create-game', {
        method: 'POST',
        body: JSON.stringify({ timePerQuestion, timePerAnswer }),
        headers: {
          Authorization: token,
        }
      })
      const response = await res.json();
      if (!response.gameId) throw new Error('no gameId returned in the response')
      router.push(`/game/${response.gameId}/presenter`)
    } catch (error) {
      setErrorMessage('There was an error handling the request.');
    }
  }

  useEffect(() => {
    setErrorMessage(gameFormValidator({ timePerQuestion, timePerAnswer }));
  }, [timePerAnswer, timePerQuestion])

  return (
    <div className="w-full max-w-lg mx-auto border-8 border-r-[var(--google-cloud-blue)] border-t-[var(--google-cloud-red)] border-b-[var(--google-cloud-green)] border-l-[var(--google-cloud-yellow)]">
      <form className="bg-white px-8 py-12" onSubmit={onCreateGameSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-bold mb-2" htmlFor="timePerQuestion">
            Time (in seconds) to answer the question
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 leading-tight focus:outline-none focus:shadow-outline"
            id="timePerQuestion"
            type="number"
            value={timePerQuestion}
            onChange={(event) => setTimePerQuestion(parseInt(event.target.value))}
            placeholder={defaultTimePerQuestion.toString()}
          />
        </div>
        <div className="mb-6">
          <label className="block text-sm font-bold mb-2" htmlFor="timePerAnswer">
            Time (in seconds) to review the answers
          </label>
          <input
            className="shadow appearance-none border rounded w-full py-2 px-3 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            id="timePerAnswer"
            type="number"
            value={timePerAnswer}
            onChange={(event) => setTimePerAnswer(parseInt(event.target.value))}
            placeholder={defaultTimePerAnswer.toString()}
          />
          <p className="text-red-500 text-xs italic">{errorMessage}</p>
        </div>
        <center>
          <BigColorBorderButton type="submit">
            Create Game
          </BigColorBorderButton>
        </center>
      </form>
    </div>
  )
}
