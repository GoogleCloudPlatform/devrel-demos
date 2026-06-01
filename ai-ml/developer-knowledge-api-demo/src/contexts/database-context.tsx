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

'use client';

/**
 * @file database-context.tsx
 * @description Provides a React context for interacting with the local SQLite database.
 * Why it matters: Exposes the DB connection status and execution functions to the app.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { ready, exec, select } from '@/lib/db';

// Interface for the database context.
interface DatabaseContextType {
  isReady: boolean;
  exec: typeof exec;
  select: typeof select;
}

// The context for the database state.
const DatabaseContext = createContext<DatabaseContextType | undefined>(undefined);

// DatabaseProvider component that initializes the database and provides access
// to database operations via context.
export function DatabaseProvider({ children }: { children: React.ReactNode }) {
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    ready.then(() => {
        setIsReady(true);
    });
  }, []);

  return (
    <DatabaseContext.Provider value={{ isReady, exec, select }}>
      {children}
    </DatabaseContext.Provider>
  );
}

// Custom hook to use the database context.
export function useDatabase() {
  const context = useContext(DatabaseContext);
  if (context === undefined) {
    throw new Error('useDatabase must be used within a DatabaseProvider');
  }
  return context;
}
