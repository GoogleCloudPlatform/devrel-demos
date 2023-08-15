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
import { signInAnonymously } from "firebase/auth";
import { auth } from "@/app/lib/firebase-client-initialization";
import BigColorBorderButton from "./big-color-border-button";

export default function SignInButton() {
  const onSignInClick = async () => {
    signInAnonymously(auth);
  }

  return (
    <button onClick={onSignInClick} className={`text-gray-700 hover:underline hover:decoration-[var(--google-cloud-blue)] hover:text-black block rounded-md px-3 py-2 text-base font-medium`}>
      Sign In
    </button>
  )
}
