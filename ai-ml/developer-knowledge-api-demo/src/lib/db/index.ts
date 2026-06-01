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
 * @file index.ts (db)
 * @description Initializes and manages the local SQLite database via WebAssembly and OPFS.
 * Why it matters: Provides persistence for user settings in a local-first architecture.
 */

let promiser: any = null;
let dbId: string | null = null;

// Initializes the SQLite database worker and opens the database.
const initPromise = (async () => {
  try {
    if (typeof window === 'undefined') return; // Ensure client-side only

    console.log('Initializing SQLite Worker...');
    // Load dynamically from public folder to bypass Next.js build issues
    // @ts-ignore
    const module = await import(/* webpackIgnore: true */ '/sqlite/sqlite3-worker1-promiser.mjs');
    const sqlite3Worker1Promiser = module.default;
    promiser = await new Promise((resolve) => {
      const _promiser = sqlite3Worker1Promiser({
        // @ts-ignore
        onready: () => {
          resolve(_promiser);
        },
        // Explicitly point to the worker script in public folder
        worker: () => new Worker(new URL('/sqlite/sqlite3-worker1.js', window.location.href))
      });
    });

    console.log('SQLite Worker Ready. Opening Database...');

    // Open the database (OPFS)
    const openResponse = await promiser('open', {
      filename: 'file:docsetlm.sqlite3?vfs=opfs',
    });

    dbId = openResponse.dbId;
    console.log('Database Opened:', dbId);

    // Initialize Schema
    await promiser('exec', {
      dbId,
      sql: `CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  name TEXT,
  preferences_json TEXT,
  created_at INTEGER
  );`
    });
    console.log('Schema Initialized');

  } catch (e) {
    console.error('Failed to initialize SQLite:', e);
  }
})();

// A promise that resolves when the database is ready.
export const ready = initPromise;

// Executes a SQL command on the database.
export async function exec(sql: string, bind?: any[]) {
  await ready;
  if (!promiser || !dbId) throw new Error('Database not initialized');
  return promiser('exec', { dbId, sql, bind });
}

// Executes a SQL query and returns the result rows as objects.
export async function select(sql: string, bind?: any[]) {
  await ready;
  if (!promiser || !dbId) throw new Error('Database not initialized');
  const res = await promiser('exec', { dbId, sql, bind, returnValue: 'resultRows', rowMode: 'object' });
  return res.result.resultRows;
}
