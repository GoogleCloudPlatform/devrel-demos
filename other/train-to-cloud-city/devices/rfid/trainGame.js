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

const { StringDecoder } = require("node:string_decoder");
const {
  validateCargo,
  updateLocation,
  submitActualCargo
} = require("./utils/firestoreHelpers.js");

// Cargo reading
let beginReading = false;
let holdCargo = [];

/**
 * evaluateRfidTags
 * ----------------------
 */ 
async function evaluateRfidTags(chunk, checkpoint, reader) { 
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
      submitActualCargo(holdCargo).then((res) => {
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

module.exports = {
  evaluateRfidTags
};
