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
 * @file utils.ts
 * @description Contains helper functions for class name merging (cn) using clsx and tailwind-merge.
 * Why it matters: Used extensively for dynamic styling in components.
 */

import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

// Combines class names using clsx and tailwind-merge to handle conflicts.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
