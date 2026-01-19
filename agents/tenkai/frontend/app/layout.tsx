import type { Metadata } from "next";
import { Inter, Roboto_Mono } from "next/font/google";
import { Sidebar } from "@/components/layout/Sidebar";
import { ThemeProvider } from "@/components/ThemeProvider";
import { SidebarProvider } from "@/components/layout/SidebarContext";
import { MainLayoutWrapper } from "@/components/layout/MainLayoutWrapper";
import { TooltipProvider } from "@/components/ui/tooltip";
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
      <body className={`${inter.variable} ${robotoMono.variable} bg-background text-foreground antialiased`}>
        <ThemeProvider defaultTheme="dark">
          <SidebarProvider>
            <TooltipProvider>
              <MainLayoutWrapper>{children}</MainLayoutWrapper>
            </TooltipProvider>
          </SidebarProvider>
          <Toaster position="bottom-right" theme="dark" closeButton richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
