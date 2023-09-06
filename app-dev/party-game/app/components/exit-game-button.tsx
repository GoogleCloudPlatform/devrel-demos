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

'use client';

import useFirebaseAuthentication from '@/app/hooks/use-firebase-authentication';
import {useRouter} from 'next/navigation';
import {exitGameAction} from '@/app/actions/exit-game';
import {getToken} from 'firebase/app-check';
import {appCheck} from '@/app/lib/firebase-client-initialization';

export default function ExitGameButton({gameId}: { gameId: string }) {
  const authUser = useFirebaseAuthentication();
  const router = useRouter();

  const onExitGameClick = async () => {
    const appCheckTokenResponse = await getToken(appCheck, false);
    const appCheckToken = appCheckTokenResponse.token;
    const token = await authUser.getIdToken();
    await exitGameAction({gameId, token, appCheckToken});
    router.push('/');
  };

  return (
    <div>
      <button onClick={onExitGameClick} className={`border mt-1 p-2`}>◄ Exit Game</button>
    </div>
  );
}
