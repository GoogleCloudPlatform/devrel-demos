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
      <button onClick={() => onDeleteGameClick(gameRef)} className={`m-2 mt-20 p-2 text-gray-700 hover:underline hover:decoration-[var(--google-cloud-red)] hover:text-black block rounded-md px-3 py-2 text-base font-medium`}>Delete Game</button>
    </div>
  )
}
