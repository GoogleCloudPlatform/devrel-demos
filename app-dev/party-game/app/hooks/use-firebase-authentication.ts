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

import {useEffect, useState} from 'react';
import {auth} from '@/app/lib/firebase-client-initialization';
import {IdTokenResult, User} from 'firebase/auth';

export const emptyUser: User = {
  emailVerified: false,
  isAnonymous: false,
  metadata: {},
  providerData: [],
  refreshToken: '',
  tenantId: null,
  delete: function(): Promise<void> {
    throw new Error('Function not implemented.');
  },
  getIdToken: function(): Promise<string> {
    throw new Error('Function not implemented.');
  },
  getIdTokenResult: function(): Promise<IdTokenResult> {
    throw new Error('Function not implemented.');
  },
  reload: function(): Promise<void> {
    throw new Error('Function not implemented.');
  },
  toJSON: function(): object {
    throw new Error('Function not implemented.');
  },
  displayName: null,
  email: null,
  phoneNumber: null,
  photoURL: null,
  providerId: '',
  uid: '',
};

const useFirebaseAuthentication = () => {
  const [authUser, setAuthUser] = useState<User>(emptyUser);

  useEffect(() => {
    const unlisten = auth.onAuthStateChanged(
        (authUser) => {
        authUser ?
          setAuthUser(authUser) :
          setAuthUser(emptyUser);
        },
    );
    return () => {
      unlisten();
    };
  }, []);

  return authUser;
};

export default useFirebaseAuthentication;
