// Copyright 2024 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

const required = (value) => (value ? undefined : "Required");
const composeValidators =
  (...validators) =>
  (value) =>
    validators.reduce(
      (error, validator) => error || validator(value),
      undefined,
    );

/**
 * validateServices
 * --------------------------
 *  TODO: Call external service validator api to ensure listed services
 *  given are valid for the pattern.
 */
const validateServices = async (pattern, proposal) => {
  const { checkpoints } = pattern;
  const { service_slugs } = proposal;

  let matchedCheckpoints = [];
  let unmatchedCheckpoints = [];

  checkpoints?.map((c, index) => {
    // Check if any are found, push to list
    // * = any service can fit
    const matchedServices = c?.satisfying_services?.filter(
      (s) => s === "*" || service_slugs.includes(s),
    );
    matchedServices.length
      ? matchedCheckpoints.push(index)
      : unmatchedCheckpoints.push(index);
  });

  const result = {
    proposal,
    pattern,
    unmatchedCheckpoints,
    matchedCheckpoints,
  };

  if (unmatchedCheckpoints.length) {
    throw new Error(
      "Patterns between proposal and mission do not match",
      result,
    );
    return;
  }

  return Promise.resolve({ message: "Services match!", result });
};

export { validateServices, required, composeValidators };
