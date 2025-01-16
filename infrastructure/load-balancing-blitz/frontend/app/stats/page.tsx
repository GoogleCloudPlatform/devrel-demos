'use client'

import React from 'react'
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Stats from "@/components/Stats";

export default function StatsPage() {
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
      <Stats />
    </main>
  );
}
