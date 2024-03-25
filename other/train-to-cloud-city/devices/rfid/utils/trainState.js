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

// Cargo reading
let beginReading = false;
let holdCargo = [];


/**
 * setMissionPattern
 * ----------------------
 * high complex - 3300348D69E3
 * medium complex -  33003558732D
 * low complex - 0D0088F32B5D
 */ 
async function setMissionPattern(chunk, reader) {
  const mission = await getMatchingService({ chunk });
  const ref = db.collection("global").doc("proposal");
  try {
    await ref.update({ pattern_slug: mission }, { merge: true });
    console.log(`Mission has been read: ${JSON.stringify(mission)}`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * readTrain
 * ----------------------
 */ 
async function readTrain(chunk, checkpoint, reader) { 
  // Redirect to mission set, this should reset entire actual_cargo 
  if(reader.location === 'mission_check') {
    await setMissionPattern(chunk, reader);
    return;
  }
  
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
      // marking current location
      //await updateLocation(chunk, checkpoint);
    } catch(error) {
      console.error(error);
    }
  }
   
  // BACK: At tailend of train, wrap up and send read cargo to firestore
  if(isBackCar) {
    beginReading = false;
    // TODO: save actual_cargo to firestore
    // TODO: pubsub metric to log beginning game (for event)
    // Verification happens at the station (checkpoint 0)
    if(reader.location  === 'station') {
      Promise.all([ updateCargos(holdCargo), validateCargo(holdCargo)])
      .then((res) => {
        console.log(JSON.stringify(res));
      })
      .catch((error) => {
        console.error(error);
      });
    
      // clear holding cargo
      holdCargo = [];
      
      // TODO: set signal lights
    }
  }
}

/**
 * getMatchingService
 * ----------------------
 */
async function getMatchingService(id) {
  const serviceRef = db.collection("tags");
  let services = [];  
  try {
    const snapshot = await serviceRef.get();
    snapshot.docs.forEach((doc) => {
      const chunk = new String(id?.chunk);
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
 * updateCargos
 *-------------------
 * chunks -> rfid tag id
 */
async function updateCargos(chunks) {
  let cargos = [];

  chunks?.forEach(async chunk => {
    const buffer = Buffer.from(JSON.stringify({ chunk }));
    const id = JSON.parse(buffer.toString());
    // Match read rfid chunk with correct service
    const matchingService = await getMatchingService(id);
    matchingService && cargos.push(matchingService);
  });

  // Updates actual_cargo state with newly read service
  const ref = db.collection("global").doc("cargo");

  try {
    await ref.update({ actual_cargo: cargos}, { merge: true });
    console.log(`Cargos read ${JSON.stringify(cargos)}`);
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
  const ref = db.collection("global").doc("cargo");
  try {
    const trainUpdate = {
      actual_location: index,
    }; 
    await ref.update(trainUpdate, { merge: true });
    console.log(`Passed checkpoint ${index}`);
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
  const proposalRef = db.collection("global").doc("proposal");

  // TODO: Check train mailbox (listener on mailbox)
  // Retrieve proposal result too?
  /*
  try {
    const snapshot = await proposalRef.get();
    const { proposal_result } = snapshot.data();
    
    // TODO: If proposal result is successful (victory lap, set signal lights green)
    // The game session is completed
    // if not, the game is still going.
    // (move back to station, set signal lights green up to missing step)

    console.log(`Proposal result is  ${JSON.stringify(proposal_result)}.`);
  } catch(error) {
    console.error(error);
  }*/
}

module.exports = {
  readTrain,
  setMissionPattern,
  validateCargo,
  updateLocation,
  updateCargos
};
