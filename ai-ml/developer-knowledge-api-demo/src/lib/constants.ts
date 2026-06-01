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
 * @file constants.ts
 * @description Defines application-wide constants for layout, tabs, and storage keys.
 * Why it matters: Centralizes configuration values to ensure consistency across the app.
 */

// The default sidebar width for the application.
export const DEFAULT_SIDEBAR_WIDTH = 256;

// Object containing the application tab identifiers.
export const APP_TABS = {
  SEARCH: 'search',
  SOURCES: 'sources',
} as const;

// Type alias for the application tab identifiers.
export type AppTab = typeof APP_TABS[keyof typeof APP_TABS];

// Object containing the display labels for the application tabs.
export const APP_TAB_LABELS = {
  [APP_TABS.SEARCH]: 'Search',
  [APP_TABS.SOURCES]: 'Knowledge Sources',
} as const;

// Object containing the storage keys used in the application.
export const STORAGE_KEYS = {
  USERS: 'docsetlm_users',
  CURRENT_USER_ID: 'docsetlm_current_user_id',
} as const;

// The default user name for the application.
export const DEFAULT_USER_NAME = 'Demo Project';
