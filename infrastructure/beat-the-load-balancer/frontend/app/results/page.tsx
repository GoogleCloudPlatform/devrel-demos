'use client'

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Stats from "@/components/Stats";

export default function ResultsPage() {
  const router = useRouter()

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      switch (event.code) {
        case 'KeyS':
          router.push('/');
      }
    };
    window.addEventListener("keydown", handleKeyDown);

    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [router]);



  return (
    <main className="min-h-screen items-center justify-between p-24">
      <div className="flex items-center justify-between">
        <Link
          href="/"
          className="group rounded-lg border border-transparent px-5 py-4 transition-colors hover:border-gray-300 hover:bg-gray-100 hover:dark:border-neutral-700 hover:dark:bg-neutral-800/30"
        >
          <h2 className={`mb-3 text-2xl font-semibold`}>
            Press S to return to Home{" "}
            <span className="inline-block transition-transform group-hover:translate-x-1 motion-reduce:transform-none">
              -&gt;
            </span>
          </h2>
        </Link>
      </div>
      <Stats />
    </main>
  );
}
