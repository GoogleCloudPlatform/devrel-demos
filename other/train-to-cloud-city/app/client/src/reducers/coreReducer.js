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

import { createSlice } from "@reduxjs/toolkit";
import {
  getInitialWorldState,
  getWorldSimulation,
  getServices,
  getPatterns,
  selectPattern,
  updateSelectedPattern
} from "../actions/coreActions";

const initialState = {
  selectedPattern: {},
  services: [],
  patterns: [],
  worldState: [],
  simulationState: [],
};

const coreSlice = createSlice({
  name: "core",
  initialState,
  extraReducers: (builder) => {
    builder
      // Note: intentionally using same property worldState for
      // both actual and simulated world state (doesn't matter for web app)
      // They just need to have one source of truth.
      .addCase(getInitialWorldState.fulfilled, (state, action) => {
        state.worldState = action?.payload?.state;
        return state;
      })
      .addCase(getWorldSimulation.fulfilled, (state, action) => {
        state.worldState = action?.payload?.simulationState;
        return state;
      })
      .addCase(getServices.fulfilled, (state, action) => {
        state.services = action?.payload?.services;
        return state;
      })
      .addCase(getPatterns.fulfilled, (state, action) => {
        state.patterns = action?.payload?.patterns;
        return state;
      })
      .addCase(updateSelectedPattern.fulfilled, (state, action) => {
        const pattern = action?.payload?.selectedPattern;
        state.selectedPattern = pattern;
        return state;
      })
      .addDefaultCase((state, action) => initialState);
  },
});

export default coreSlice.reducer;
