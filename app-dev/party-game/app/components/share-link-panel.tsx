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

import {useState} from 'react';
import QRCode from 'react-qr-code';

export default function ShareLinkPanel({gameId}: { gameId: string }) {
  const gameShareLink = `${location.protocol}//${location.host}/game/${gameId}`;
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyShareLink = () => {
    navigator.clipboard.writeText(gameShareLink);
    setIsCopied(true);
  };

  return (
    <div>
      <div>
        Scan this QR code to join the game:
        <QRCode value={gameShareLink} />
      </div>
      <button onClick={copyShareLink} className={`border m-2 p-2`}>Click to Copy Share Link</button>
      <br />
      <p>
        {isCopied ? 'Link copied to clipboard' : ''}
      </p>
    </div>
  );
}
