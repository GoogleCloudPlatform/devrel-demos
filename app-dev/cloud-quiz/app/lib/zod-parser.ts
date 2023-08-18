/**
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { z } from "zod";

export const unknownValidator = (body: unknown, Schema: z.ZodType) => {
  // Validate request
  try {
    Schema.parse(body);
  } catch (error) {
    // return the first error
    if (error instanceof z.ZodError) {
      return error.issues[0].message;
    }
    throw error;
  }

  return '';
}

export const unknownParser = (body: unknown, Schema: z.ZodType) => {
  // Validate request
  const errorMessage = unknownValidator(body, Schema);
  if (errorMessage) {
    throw new Error(errorMessage)
  }
  return Schema.parse(body);
}