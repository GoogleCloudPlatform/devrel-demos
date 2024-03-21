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

import { createAsyncThunk } from "@reduxjs/toolkit";

export const DELETE_CAR = "DELETE_CAR";
export const ADD_CAR = "ADD_CAR";

const testFetch = createAsyncThunk("testFetch", async () => {
  // Do we want to keep this in bigquery or add it to browser cache if
  // we're trying to keep the logic lean
  const headers = {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  };

  let execution;

  try {
    const response = await fetch(
      `http://127.0.0.1:4000/createAttemptWorkflow`,
      { mode: "cors" },
      headers,
    );
    execution = await response.json();
  } catch (e) {
    console.error(e);
  }

  return execution;
});

/**
 * -----------------
 * addCar
 * -----------------
 * Adds a new "train coach" by taking in a "serviceId" that maps
 * to an accompanying cloud workflow control statement(s)
 */
// TODO: serviceId is currently placeholder / the service shape still tbd
const addCar = (serviceId) => {
  return {
    type: ADD_CAR,
    payload: { serviceId },
  };
};

/**
 * -----------------
 * deleteCar
 * -----------------
 * Removes a "train coach" by taking in a "serviceId" that maps
 * to an accompanying cloud workflow control statement(s) to delete
 * from train
 */
// TODO: serviceId is currently placeholder / the service shape still tbd
const deleteCar = (serviceId) => {
  return {
    type: DELETE_CAR,
    payload: { serviceId },
  };
};

export { addCar, deleteCar, testFetch };
