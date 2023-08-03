"use client"

import { DocumentReference } from "firebase/firestore";
import { useState } from "react"
import QRCode from "react-qr-code";

export default function ShareLinkPanel({ gameRef }: { gameRef: DocumentReference }) {
  const gameShareLink = `${location.protocol}//${window.location.host}/game/${gameRef.id}`;
  const [isCopied, setIsCopied] = useState<Boolean>(false);

  const copyShareLink = () => {
    navigator.clipboard.writeText(gameShareLink);
    setIsCopied(true);
  }

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
  )
}
