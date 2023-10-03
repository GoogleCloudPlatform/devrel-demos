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

import useActiveGameList from '@/app/hooks/use-active-game-list';
import {useRouter} from 'next/navigation';
import {useEffect} from 'react';

export default function Home() {
  const {activeGameList} = useActiveGameList();
  const router = useRouter();

  useEffect(() => {
    if (activeGameList.length > 0) {
      const firstGameId = activeGameList[0].id;
      router.push(`/game/${firstGameId}`);
    }
  }, [activeGameList, router]);

  return (
    <div>
      <center className="p-8">
        Waiting for a game.
      </center>
    </div>
  );
}
