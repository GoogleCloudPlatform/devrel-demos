"use client"

export default function ExitGameButton({ setGameRef }: { setGameRef: Function }) {
  return (
    <div>
        <button onClick={() => setGameRef(null)} className={`border mt-20`}>Exit Game</button>
    </div>
  )
}
