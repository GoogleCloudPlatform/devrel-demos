import type { Metadata } from "next";
import Link from "next/link";
import { Inter, Roboto_Mono } from "next/font/google";
import { SidebarNav } from "@/components/SidebarNav";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

const robotoMono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
});

export const metadata: Metadata = {
  title: "Tenkai | Agentic Experimentation Dashboard",
  description: "Benchmarking and optimizing tool-calling behaviors of AI agents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${robotoMono.variable} bg-[#020617] text-white antialiased`}>
        <div className="flex min-h-screen">
          {/* Sidebar */}
          <aside className="w-64 glass border-r h-screen sticky top-0 flex flex-col p-6">
            <div className="mb-10">
              <Link href="/">
                <h1 className="text-2xl font-bold tracking-tighter gradient-text cursor-pointer">TENKAI</h1>
              </Link>
              <p className="text-[10px] text-zinc-500 uppercase tracking-widest font-semibold mt-1">Experimentation Framework</p>
            </div>

            <SidebarNav />

            <div className="mt-auto pt-6 border-t border-white/5 text-xs text-zinc-500">
              <p className="opacity-70">This is not an officially supported Google product.</p>
            </div>
          </aside>

          {/* Main Content */}
          <main className="flex-1 overflow-auto">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
