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
import firebaseInstance from "../Firebase";

/**** Getters ****/

/**
 * -----------------
 * getServices
 * -----------------
 */
export const getServices = createAsyncThunk("getServices", async () => {
  const ref = firebaseInstance.db.collection("services_by_category");
  const services = await ref.get().then((querySnapshot) => {
    let serviceList = [];
    querySnapshot.docs.forEach(doc => serviceList.push(`${doc.id}`));
    return serviceList;
  });

  return { services };
});

/**
 * -----------------
 * getPatterns
 * -----------------
 */
export const getPatterns = createAsyncThunk("getPatterns", async () => {
  const ref = firebaseInstance.db.collection("patterns");
  const patterns = await ref.get().then((querySnapshot) => {
    let patternList = [];
    querySnapshot.docs.forEach(doc => patternList.push(doc.data()));
    return patternList;
  });

  return { patterns };
});

/**
 * -----------------
 * getInitialWorldState
 * -----------------
 */
export const getInitialWorldState = createAsyncThunk(
  "getInitialWorldState",
  async () => {
    const ref = firebaseInstance.db.collection("global");
    const state = await ref.get().then((querySnapshot) => {
      let world = {};
      querySnapshot.docs.forEach(doc => world[doc.id] = doc.data());
      return world;
    });

    return { state };
  },
);

/**
 * -----------------
 * getWorld
 * -----------------
 */
export const getWorld = async ({ dispatch, isSimulator, pattern }) => {
  if(isSimulator) {
    await worldSimulationStateUpdated(dispatch);
  } else {
    Promise.all([
      worldStateUpdated(dispatch),
      dispatch?.(updateSelectedPattern(pattern))
    ])
      .then(res => {
        console.log(res);
      })
      .catch(err => {
        console.error(err);
      });
  }
};

/**
 * -----------------
 * getWorldSimulation
 * -----------------
 */
export const getWorldSimulation = createAsyncThunk(
  "getWorldSimulation",
  async (changeType) => {
    const ref = firebaseInstance.db.collection("global_simulation");
    const simulationState = await ref.get().then((querySnapshot) => {
      let world = {};
      querySnapshot.docs.forEach(doc => world[doc.id] = doc.data());
      return world;
    });
    
    return { simulationState: { ...simulationState, changeType } };
  },
);

/**** Updates ****/

/**
 * -----------------
 * updateSelectedPattern
 * -----------------
 */
export const updateSelectedPattern = createAsyncThunk(
  "updateSelectedPattern",
  async (pattern) => {
    const ref = firebaseInstance.db.collection("global").doc("proposal");
    const selectedPattern = await ref.update({ pattern_slug: pattern?.slug });
    
    return { selectedPattern: pattern };
  });


/**** Listeners ****/
/**
 * -----------------
 * worldStateUpdated
 * -----------------
 */
export const worldStateUpdated = async (dispatch) => {
  const ref = firebaseInstance.db.collection("global");

  await ref.onSnapshot((snapshot) => {
    snapshot.docChanges().forEach((change) => {
      dispatch?.(getInitialWorldState());
    });
  });
};

/**
 * -----------------
 * worldSimulationStateUpdated
 * -----------------
 */
export const worldSimulationStateUpdated = async (dispatch) => {
  const ref = firebaseInstance.db.collection("global_simulation");
  await ref.onSnapshot((snapshot) => {
    snapshot.docChanges().forEach((change) => {
      dispatch?.(getWorldSimulation(change.type));
    });
  });
};

/**
 * -----------------
 * trainMailboxUpdated
 * -----------------
export const trainMailboxUpdated = async (dispatch) => {
  const ref = firebaseInstance.db.collection("global").doc("train_mailbox");
  await ref.onSnapshot((snapshot) => {
    snapshot.docChanges().forEach(change => {
      dispatch?.(getWorldSimulation());
    });
  });
};

/**
 * -----------------
 * sessionMailboxUpdated
 * -----------------
export const sessionMailboxUpdated = async (dispatch) => {
  const ref = firebaseInstance.db.collection("global").doc("session_mailbox");
  await ref.onSnapshot((snapshot) => {
    snapshot.docChanges().forEach((change) => {
      dispatch?.(getWorldSimulation());
    
    });
  });
};
*/

