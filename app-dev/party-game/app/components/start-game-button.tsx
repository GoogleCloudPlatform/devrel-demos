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

import './big-color-border-button.css';
import BigColorBorderButton from '@/app/components/big-color-border-button';
import {nudgeGameAction} from '@/app/actions/nudge-game';
import {getTokens} from '@/app/lib/client-token-generator';
import {gameStates} from '../types';

export default function StartGameButton({gameId}: {gameId: string}) {
  const onStartGameClick = async () => {
    const tokens = await getTokens();
    const desiredState = {
      state: gameStates.AWAITING_PLAYER_ANSWERS,
      currentQuestionIndex: 0,
    };
    nudgeGameAction({gameId, desiredState, tokens});
  };

  return (
    <BigColorBorderButton onClick={onStartGameClick}>
      Start Game Now ►
    </BigColorBorderButton>
  );
}
