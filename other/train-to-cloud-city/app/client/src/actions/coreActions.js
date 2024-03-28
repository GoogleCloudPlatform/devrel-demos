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
 * getWorldState
 * -----------------
 */
export const getWorldState = createAsyncThunk(
  "getWorldState",
  async (collectionName = "global") => {
    const ref = firebaseInstance.db.collection(collectionName);
    const snapshot = await ref.get();
    let world = {};
    snapshot.docs.forEach((doc) => (world[doc.id] = doc.data()));
    return world;

    return { state: world };
  },
);

/**
 * -----------------
 * getServices
 * -----------------
 */
export const getServices = createAsyncThunk("getServices", async () => {
  const ref = firebaseInstance.db.collection("services");
  const services = await ref.get().then((querySnapshot) => {
    let serviceList = [];
    querySnapshot.docs.forEach((doc) => serviceList.push(`${doc.id}`));
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
    querySnapshot.docs.forEach((doc) => patternList.push(doc.data()));
    return patternList;
  });

  return { patterns };
});

/**** Updates ****/

/**
 * -----------------
 * updateCargo
 * -----------------
 * Submit loaded cargo to firestore for validation
 */
export const updateCargo = createAsyncThunk(
  "updateCargo",
  async (cargo = [], collectionName = "global") => {
    const cargoRef = firebaseInstance.db
      .collection(collectionName)
      .doc("cargo");
    try {
      await cargoRef.update({ actual_cargo: cargo });
    } catch (error) {
      console.error(error);
    }
  },
);

/**
 * -----------------
 * stopMission
 * -----------------
 * Resets entire game and redirect user to homebase
 */
export const stopMission = createAsyncThunk(
  "stopMission",
  async (collectionName = "global") => {
    const cargoRef = firebaseInstance.db
      .collection(collectionName)
      .doc("cargo");
    const patternRef = firebaseInstance.db
      .collection(collectionName)
      .doc("proposal");

    return Promise.all([
      cargoRef.update({ actual_cargo: [] }),
      patternRef.update({ pattern_slug: "" }),
    ]);
  },
);

// ============== Listeners ============== //

/**
 * -----------------
 * worldStateUpdated
 * -----------------
 */
export const worldStateUpdated = async (
  dispatch,
  collectionName = "global",
) => {
  const ref = firebaseInstance.db.collection(collectionName);
  await ref.onSnapshot((snapshot) => {
    snapshot.docChanges().forEach((change) => {
      dispatch?.(getWorldState());
    });
  });
};

/**
 * -----------------
 * trainMailboxUpdated
 * -----------------
 */
export const trainMailboxUpdated = async (
  callback = () => {},
  collectionName = "global",
) => {
  const ref = firebaseInstance.db
    .collection(collectionName)
    .doc("train_mailbox");
  try {
    await ref.onSnapshot((snapshot) => callback(snapshot.data()));
  } catch (error) {
    console.error(error);
  }
};

/**
 * -----------------
 * proposalUpdated
 * -----------------
 */
export const proposalUpdated = async (
  callback = () => {},
  collectionName = "global",
) => {
  const ref = firebaseInstance.db.collection(collectionName).doc("proposal");
  try {
    await ref.onSnapshot((snapshot) => callback(snapshot.data()));
  } catch (error) {
    console.error(error);
  }
};

/**
 * -----------------
 * trainUpdated
 * -----------------
 */
export const trainUpdated = async (
  callback = () => {},
  collectionName = "global",
) => {
  const ref = firebaseInstance.db.collection(collectionName).doc("train");
  try {
    await ref.onSnapshot((snapshot) => callback(snapshot.data()));
  } catch (error) {
    console.error(error);
  }
};

/**
 * -----------------
 * cargoUpdated
 * -----------------
 */
export const cargoUpdated = async (
  callback = () => {},
  collectionName = "global",
) => {
  const ref = firebaseInstance.db.collection(collectionName).doc("cargo");
  try {
    await ref.onSnapshot((snapshot) => callback(snapshot.data()));
  } catch (error) {
    console.error(error);
  }
};

/**
 * -----------------
 * signalsUpdated
 * -----------------
 */
export const signalsUpdated = async (
  callback = () => {},
  collectionName = "global",
) => {
  const ref = firebaseInstance.db.collection(collectionName).doc("signals");
  try {
    await ref.onSnapshot((snapshot) => callback(snapshot.data()));
  } catch (error) {
    console.error(error);
  }
};

/**
 * -----------------
 * updateInputMailbox
 * -----------------
 */
export const updateInputMailbox = async (eventString) => {
  const ref = firebaseInstance.db.collection("global").doc("input_mailbox");
  try {
    await ref.update({ input: eventString });
  } catch (error) {
    console.error(error);
  }
};
