// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

/**
 * @file layout.tsx
 * @description The root layout component for the application.
 * Why it matters: Sets up the HTML document structure, fonts, and global context providers.
 */

import type {Metadata} from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Developer Knowledge API Demo',
  description: 'AI-powered documentation for developers',
};

import { UserProvider } from '@/contexts/user-context';
import { DatabaseProvider } from '@/contexts/database-context';

/**
 * The root layout component that wraps all pages.
 * It sets up the HTML structure, loads fonts, and provides context providers.
 * 
 * @param children The child components to render within the layout.
 * @returns The complete HTML document structure.
 */
export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="font-body antialiased" suppressHydrationWarning>
        <DatabaseProvider>
          <UserProvider>
            {children}
          </UserProvider>
        </DatabaseProvider>
      </body>
    </html>
  );
}
