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
 * @file user-context.tsx
 * @description Manages user state, preferences, and profile persistence in local storage and SQLite.
 * Why it matters: Centralizes user identity and settings across the application.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import { useDatabase } from '@/contexts/database-context';
import { STORAGE_KEYS, DEFAULT_USER_NAME } from '@/lib/constants';
import type { ProductConfig, ProviderConfig } from '@/lib/dkg/products';

const STORAGE_KEY_USERS = STORAGE_KEYS.USERS;
const STORAGE_KEY_CURRENT_USER_ID = STORAGE_KEYS.CURRENT_USER_ID;

// Interface for user preferences.
export interface UserPreferences {
  dkg?: {
    selectedProducts: string[];
    modules: { explain: boolean; generate: boolean };
  };
  customSources?: ProductConfig[];
  customProviders?: ProviderConfig[];
  subscribedPresetIds?: string[];
  sidebarWidth?: number;
}

// Interface for a user.
export interface User {
  id: string;
  name: string;
  preferences: UserPreferences;
  createdAt: number;
}

// Interface for the user context.
interface UserContextType {
  currentUser: User | null;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
  isHydrated: boolean;
}

// Context for user state
const UserContext = createContext<UserContextType | undefined>(undefined);

// UserProvider component that manages user state, preferences, and persistence.
export function UserProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isHydrated, setIsHydrated] = useState(false);
  const { isReady, exec, select } = useDatabase();

  // Load basic user metadata from local storage on mount
  useEffect(() => {
    try {
      const storedUsers = localStorage.getItem(STORAGE_KEY_USERS);
      const storedCurrentId = localStorage.getItem(STORAGE_KEY_CURRENT_USER_ID);

      if (storedUsers && storedCurrentId) {
        const parsedUsers = JSON.parse(storedUsers);
        if (parsedUsers[storedCurrentId]) {
          setCurrentUser(parsedUsers[storedCurrentId]);
        }
      }
    } catch (e) {
      console.error('Failed to load user data from user context', e);
    } finally {
      setIsLoaded(true);
    }
  }, []);

  // Hydrate Data from SQLite when DB is Ready
  useEffect(() => {
    if (!isReady || currentUser) return;

    const restoreUserFromDb = async () => {
      try {
        console.log('[UserContext] restoring user from DB...');
        const usersResult = await select('SELECT * FROM users LIMIT 1');
        if (usersResult && usersResult.length > 0) {
          const row = usersResult[0];
          let prefs = {};
          if (row.preferences_json) {
            try {
              prefs = JSON.parse(row.preferences_json);
            } catch (e) {
              console.error('Failed to parse preferences_json for user', row.id, e);
            }
          }

          setCurrentUser({
            id: row.id,
            name: row.name,
            createdAt: row.created_at,
            preferences: prefs as UserPreferences
          });
        }
      } catch (e) {
        console.error('Failed to restore user from DB', e);
      }
    };

    restoreUserFromDb();
  }, [isReady, currentUser, select]);

  // Hydrate Data from SQLite when DB is Ready and User is logged in
  useEffect(() => {
    if (!isReady || !currentUser) {
      if (!isReady) setIsHydrated(false);
      return;
    }

    const hydrateUserData = async () => {
      if (!isReady || !currentUser) return;

      console.log(`[UserContext] Hydrating data for user: ${currentUser.id} (${currentUser.name})`);

      try {
        // Fetch updated user preferences from DB to ensure we have the latest
        const userRowMsg = await select('SELECT preferences_json FROM users WHERE id = ?', [currentUser.id]);
        let dbPrefs: Partial<UserPreferences> = {};
        if (userRowMsg && userRowMsg.length > 0 && userRowMsg[0].preferences_json) {
          try {
            dbPrefs = JSON.parse(userRowMsg[0].preferences_json);
          } catch (e) { console.error('Failed to parse current user preferences_json', e); }
        }

        setCurrentUser(prev => prev ? ({
          ...prev,
          preferences: {
            ...prev.preferences,
            ...dbPrefs, // Merge DB prefs (DKG, etc)
          }
        }) : null);

      } catch (e) {
        console.error('Failed to hydrate from SQLite', e);
      }
    };

    hydrateUserData().then(() => {
      setIsHydrated(true);
    });
  }, [isReady, currentUser?.id]);

  // Persist current user ID
  useEffect(() => {
    if (isLoaded) {
      if (currentUser) {
        localStorage.setItem(STORAGE_KEY_CURRENT_USER_ID, currentUser.id);
      } else {
        localStorage.removeItem(STORAGE_KEY_CURRENT_USER_ID);
      }
    }
  }, [currentUser, isLoaded]);

  // Creates a new user profile and persists it to the database if ready.
  const createUser = useCallback(async (name: string) => {
    const id = uuidv4();
    const newUser: User = {
      id,
      name,
      createdAt: Date.now(),
      preferences: {
        customProviders: [],
        customSources: []
      },
    };

    if (isReady) {
      // Create initial preferences JSON
      const initialPrefs = {
        customProviders: newUser.preferences.customProviders,
        customSources: newUser.preferences.customSources
      };

      await exec('INSERT INTO users (id, name, created_at, preferences_json) VALUES (?, ?, ?, ?)',
        [id, name, Date.now(), JSON.stringify(initialPrefs)]);
    }

    setCurrentUser(newUser);
    return id;
  }, [isReady, exec]);

  // Update preferences
  const updatePreferences = useCallback(async (prefs: Partial<UserPreferences>) => {
    if (!currentUser) return;

    console.log(`[UserContext] updatePreferences called for ${currentUser.id}`, Object.keys(prefs));

    // Create updated user with new preferences
    const updatedUser = {
      ...currentUser,
      preferences: { ...currentUser.preferences, ...prefs },
    };

    // Set the updated user
    setCurrentUser(updatedUser);

    // Persist general preferences (Theme, DKG, etc) to users table
    if (isReady) {
      const prefsToStore = { ...currentUser.preferences, ...prefs };
      try {
        await exec('UPDATE users SET preferences_json = ? WHERE id = ?',
          [JSON.stringify(prefsToStore), currentUser.id]);
      } catch (e) {
        console.error('[UserContext] Failed to update preferences_json', e);
      }

    }
  }, [currentUser, isReady, exec]);

  // Auto-create default user if no users exist
  useEffect(() => {
    if (isLoaded && !currentUser) {
      console.log(`[UserContext] No users found, creating default ${DEFAULT_USER_NAME} profile`);
      createUser(DEFAULT_USER_NAME);
    }
  }, [isLoaded, currentUser, createUser]);

  return (
    <UserContext.Provider value={{ currentUser, updatePreferences, isHydrated }}>
      {children}
    </UserContext.Provider>
  );
}

// Custom hook to use the user context.
export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return context;
}
