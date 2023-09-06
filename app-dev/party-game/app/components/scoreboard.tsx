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

import '@/app/components/player-list.css';
import useScoreboard from '@/app/hooks/use-scoreboard';

export default function Scoreboard() {
  const {currentPlayer, playerScores} = useScoreboard();

  if (playerScores.length === 0) {
    return <></>;
  }

  return (
    <div className="mt-5 w-fit m-auto">
      <center className='mt-10'>
        Scoreboard
      </center>
      {playerScores.map((playerScore) => (<div key={playerScore.uid} className="player-list-item relative" style={{display: 'block'}}>
        <div className='flex justify-between'>
          <div className='pr-4'>{playerScore.displayName}</div>
          <div>{playerScore.score}</div>
        </div>
        <div className='text-black z-50 absolute left-full min-w-fit whitespace-nowrap top-0 h-full flex p-1'>
          <div className='m-auto'>
            {currentPlayer?.uid === playerScore.uid && ' ← You!'}
          </div>
        </div>
      </div>))}
    </div>
  );
}
