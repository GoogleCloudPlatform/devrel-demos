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

import {initializeApp} from 'firebase/app';
import {getFirestore} from 'firebase/firestore';
import {getAuth} from 'firebase/auth';
import {firebaseConfig} from '@/app/lib/firebase-config';
import {AppCheck, initializeAppCheck, ReCaptchaEnterpriseProvider} from 'firebase/app-check';

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);
export const auth = getAuth(app);
export let appCheck: AppCheck;

if (typeof window !== 'undefined') {
  // Create a ReCaptchaEnterpriseProvider instance using your reCAPTCHA Enterprise
  // site key and pass it to initializeAppCheck().
  // @ts-expect-error
  if (location.hostname === 'localhost') self.FIREBASE_APPCHECK_DEBUG_TOKEN = true;
  appCheck = initializeAppCheck(app, {
    provider: new ReCaptchaEnterpriseProvider('6Lc3JP8nAAAAAPrX4s-HwUT8L-k_aMtbKGhJEq_0'),
    isTokenAutoRefreshEnabled: true, // Set to true to allow auto-refresh.
  });
}
