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
  getTrain,
  getTrainMailbox,
  getSessionMailbox,
  clearTrainMailbox,
  validateCargo,
  updateLocation,
  submitActualCargo
} = require("./utils/firestoreHelpers.js");
const { getMotor } = require("./utils/train.js");

// Cargo reading
let beginReading = false;
let holdCargo = [];

/**
 * evaluateRfidTags
 * ----------------------
 */ 
async function evaluateRfidTags(chunk, checkpoint, role) {  
  const motor = await getMotor();

  const tagId = new String(chunk); 
  const frontCar = '\x02330035AD1EB5\r';
  const backCar = '\x03\x023300348E9019\r';

  const isFrontCar = frontCar.includes(tagId);
  const isBackCar = backCar.includes(tagId);
  const isCargo = !isFrontCar && !isBackCar;

  const train = await getTrain();
  const trainMailbox = await getTrainMailbox();

  const isStationCheck = (
    role === 'station' && // current location 
    train.actual_location === 'station' &&  // database last recorded
    trainMailbox.input === 'do_check_cargo'
  );
  const isStationVictory = (
    role === 'station' && // current location 
    train.actual_location === 'station' &&  // database last recorded
    trainMailbox.input === 'do_victory_lap'
  );

  const loadingAtStation = (
    !isStationCheck && !isStationVictory &&
    role === 'station' && // current location 
    train.actual_location === 'station' 
  );

  // TODO: add in 3 states for train in if check 
  if(role === 'station') {
    // MIDDLE: In the middle of train, store cargo chunk and continue on
    if(isCargo && beginReading) {
      holdCargo.push(chunk);
      try {
        await updateLocation(chunk, role);
      } catch(error) {
        console.error(error);
      }
      return;
    }

    // FRONT: Begin reading cargo
    if(isFrontCar) {
      // TODO: read in mailbox for this check
      // if(isVictory) {
      //  motor.stop();
      //  await clearTrainMailbox(); 
      //} else {
      beginReading = true
      try {
        // marking current location
        await updateLocation(chunk, role);
      } catch(error) {
        console.error(error);
      }
    }

    // BACK: At tailend of train, wrap up and send read cargo to firestore
    if(isBackCar) {
      beginReading = false;
      // TODO: pubsub metric to log beginning game (for event)
      motor.stop();

      submitActualCargo(holdCargo).then((res) => {
        motor.setPower(40);
        console.log('Victory!');
        console.log(JSON.stringify(res));
      })
        .catch((error) => {
          motor.setPower(-10);
          console.error(error);
          // move backwards
        });
      // clear holding cargo
      holdCargo = [];

      // TODO: set signal lights
    }
  }
}

module.exports = { evaluateRfidTags };
