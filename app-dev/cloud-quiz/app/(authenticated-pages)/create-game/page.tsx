"use client"

import CreateGameForm from "@/app/components/create-game-form";
import Link from "next/link";

export default function Home() {
  return (
    <div>
      <Link href="/">
        <button className={`border mt-5 p-2`}>← Exit</button>
      </Link>
      <br />
      <CreateGameForm />
    </div>
  )
}
