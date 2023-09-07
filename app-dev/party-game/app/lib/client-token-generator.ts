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

import {appCheck, auth} from '@/app/lib/firebase-client-initialization';
import {getToken} from 'firebase/app-check';
import {Tokens} from '@/app/types';

export async function getTokens(): Promise<Tokens> {
  const appCheckTokenResponse = await getToken(appCheck, false);
  const appCheckToken = appCheckTokenResponse.token;
  const userToken = await auth.currentUser?.getIdToken();
  if (!userToken) throw new Error('no user token');
  return {userToken, appCheckToken};
}
