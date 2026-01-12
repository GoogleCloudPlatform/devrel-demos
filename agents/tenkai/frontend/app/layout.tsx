import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
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
  title: "Tenkai | Workbench",
  description: "Benchmarking and optimizing tool-calling behaviors of AI agents.",
};

import { Toaster } from "sonner";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} ${robotoMono.variable} bg-[#09090b] text-[#f4f4f5] antialiased`}>
        <Sidebar />
        <main className="ml-[240px] min-h-screen bg-[#09090b]">
          {children}
        </main>
        <Toaster position="bottom-right" theme="dark" closeButton richColors />
      </body>
    </html>
  );
}
