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
'use server';

/**
 * @file actions.ts
 * @description Defines server actions for saving and retrieving the DKG API key.
 * Why it matters: Allows the client to interact with server-side operations securely.
 */

/**
 * Retrieves the Developer Knowledge Graph API key from the environment variable.
 * 
 * @returns The API key as a string, or an empty string if not found.
 */
export async function getDkgApiKey() {
  return process.env.DEVELOPER_KNOWLEDGE_API_DEMO_KEY || '';
}
