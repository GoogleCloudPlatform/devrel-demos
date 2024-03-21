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

const { LocalStorage } = require("node-localstorage");
const { firebase, db, app, firestore } = require("./firebase.js");
const { StringDecoder } = require("node:string_decoder");
const decoder = new StringDecoder("utf8");
const sleep = ms => new Promise(r => setTimeout(r, ms));

// TODO: Find if localstorage is best place to store
let beginReading = false;
let holdCargo = [];


/**
 * readTrain
 * ----------------------
 * TODO: To replace checkpointCrossed
 */ 
async function readTrain(chunk, checkpoint) { 
  // This could be separate before the game begins
  //const patternSelected = rfid; (after backcar)
  const tagId = new String(chunk);
  // TODO: Replace with calls to firestore
  const frontCar = '\x02330035AD1EB5\r';
  const backCar = '\x03\x023300348E9019\r';
  
  const isFrontCar = frontCar.includes(tagId);
  const isBackCar = backCar.includes(tagId);
  const isCargo = !isFrontCar && !isBackCar;

  // MIDDLE: In the middle of train, store cargo chunk and continue on
  if(isCargo && beginReading) {
    holdCargo.push(chunk);
    return;
  }

  // FRONT: Begin reading cargo
  if(isFrontCar) {
    beginReading = true
    try {
      await updateLocation(chunk, checkpoint);
    } catch(error) {
      console.error(error);
    }
  }
   
  // BACK: At tailend of train, wrap up and send read cargo to firestore
  if(isBackCar) {
    beginReading = false
    actual_cargo = holdCargo
    holdCargo = []; // clear holding cargo

    // TODO: save actual_cargo to firestore
    // TODO: pubsub metric to log beginning game (for event)
    // Verification happens at the station (checkpoint 0)
    if(checkpoint === 0) {
      Promise.all([
        // updateCargo(holdCargo, 0),
        // validateCargo(holdCargo, 0)
      ])
        .catch((error) => {
          console.error(error);
        });
      // TODO: set signal lights
    }
  }
}

/**
 * getMatchingService
 * ----------------------
 */
async function getMatchingService(docId) {
  const serviceRef = db.collection("tags");
  let services = [];
  
  try {
    const snapshot = await serviceRef.get();
    snapshot.docs.forEach((doc) => {
      const chunk = new String(docId.chunk);
      const docId = new String(doc.id);
      if (chunk.includes(docId)) {
        services.push(doc.data());
      }
    });
  } catch(error) {
    console.error(error);
  }

  return services;
}

/**
 * updateCargo
 *-------------------
 * chunk -> rfid tag id
 * index -> step train is on
 */
async function updateCargo(chunk, index) {
  const buffer = Buffer.from(JSON.stringify({ chunk }));
  const docId = JSON.parse(buffer.toString());

  // Match read rfid chunk with correct service
  const matchingService = await getMatchingService(docId);
  // Updates actual_cargo state with newly read service
  const ref = db.collection("global").doc("world");
 
  try {
    const cargoSnapshot = await ref.get();
    const { train } = cargoSnapshot.data();
    
    const newCargo = {
      reader: index,
      service: matchingService,
    };
    const trainUpdate = {
      train: {
        ...train,
        actual_cargo: [...train?.actual_cargo, newCargo],
      },
    };
    await ref.update(trainUpdate, { merge: true });
    console.log(`Cargo read ${JSON.stringify(newCargo)}`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * updateLocation
 *-------------------
 * index -> step train is on
 */
async function updateLocation(chunk, index = 0) {
  const ref = db.collection("global").doc("world");
  
  try {
    const snapshot = await ref.get();
    const { train } = snapshot.data();
    const trainUpdate = {
      train: {
        ...train,
        actual_location: index,
      },
    }; 
    
    // Move train if train is not at location they need to be
    const locationReached = index === train.target_location; 

    await ref.update(trainUpdate, { merge: true });
    console.log(`Passed checkpoint ${index}`);
   
    if(locationReached) {
      await updateTrainMovement(false, 0);
    }
  } catch(error) {
    console.error(error);
  }
}

/**
 * getTrainMovement
 * --------------------------
 */
async function getTrainMovement() {
  const ref = db.collection("train");
  let movement = [];

  try {
    const snapshot = await ref.get();
    snapshot.forEach((doc) => movement.push(doc.data()));
  } catch(error) {
    console.error(error);
  }
  
  return movement?.[0];
}

async function moveTrainToCheckpoint(currentIndex, targetIndex) {
  await updateTrainMovement(currentIndex !== targetIndex, 30);
}

/**
 * updateTrainMovement
 * --------------------------
 * power: -100 (backwards) -> +100 (forward)
 */
async function updateTrainMovement(isRunning, power = 30) {
  try {
    const state = { isRunning,  power };
    const ref = db.collection("train").doc("state");
    await ref.set(state, { merge: true });
    console.log(`Train is running: ${isRunning}`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * validateCargo
 *-------------------
 * cargos[] -> list of services
 * index -> step train is on
 */
async function validateCargo(cargos) {
  const ref = db.collection("global").doc("world");

  try {
    const snapshot = await ref.get();
    const { train } = snapshot.data();
    const nextStop = train.actual_location > 2 ? 0 : train.actual_location + 1; // checkpoints 0 -> 3
    // TODO: Add in here the code to connect with validation api to pass actual cargo
    /**
     * const response = await fetch(......)
     *
     * if (response.status === 200) {
     *   // update actual_cargo
     *   // update target_location to 0 ---> move all the way around the track
     * } else {
     *   const { erroredCheckpoint } = response;
     *   // update target_location to erroredCheckpoint marker
     *   // train should move forward and then move back to station with red signal lights
     * }
     */
    const trainUpdate = {
      train: {
        ...train,
        target_location: 3,
      },
    };
    // Update new target location after successful validation
    await ref.update(trainUpdate, { merge: true });
    console.log(`Target location for train is checkpoint ${nextStop}.`);
  } catch(error) {
    console.error(error);
  }
}

module.exports = {
  readTrain,
  validateCargo,
  getTrainMovement,
  updateLocation,
  updateCargo,
  updateTrainMovement,
};
