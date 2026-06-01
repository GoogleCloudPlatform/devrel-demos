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
 * @file page.tsx
 * @description The main landing page component for the application.
 * Why it matters: Serves as the entry point for the UI, rendering the MainLayout.
 */

import { MainLayout } from '@/components/devdocs/main-layout';
import { Toaster } from "@/components/ui/toaster";
import { Suspense } from 'react';

/**
 * The main page component that renders the primary layout and toaster notifications.
 * 
 * @returns The JSX elements for the home page.
 */
export default async function Home() {
  return (
    <>
      <Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>
        <MainLayout />
      </Suspense>
      <Toaster />
    </>
  );
}
