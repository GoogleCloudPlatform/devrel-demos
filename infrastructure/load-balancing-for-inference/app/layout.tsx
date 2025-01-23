import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
// import AudioButton from "@/components/AudioButton";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Load Balancing Blitz",
  description: "Race against Google Cloud load balancer to see who can route internet traffic faster in this timed showdown!",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={inter.className}>
        {/* <AudioButton /> */}
        {children}
      </body>
    </html>
  );
}
