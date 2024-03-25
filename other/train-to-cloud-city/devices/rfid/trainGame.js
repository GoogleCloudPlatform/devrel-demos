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

let goingOnVictoryLap = false;

/**
 * readCargo
 * ----------------------
 */ 
async function readCargo(chunk, checkpoint, role) {  
  let actualCargo = [];

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
    beginReading = true
    try {
      await updateLocation(chunk, role);
    } catch(error) {
      console.error(error);
    }
  }

  // BACK: At tailend of train, wrap up and send read cargo to firestore
  if(isBackCar) {
    beginReading = false;
    const actualCargo = holdCargo;
    // clear any previously read cargo
    holdCargo = [];
  }

  return actualCargo;
}


/**
 * startGameLoop
 * ----------------------
 * Main game loop
 */ 
async function startGameLoop(chunk, checkpoint, role) {  
  if(role !== 'station') {
    return;
  }
  const motor = await getMotor();
  const trainMailbox = await getTrainMailbox();
  
  motor.stop();
  
  if(trainMailbox.input === 'do_check_cargo') {
    motor.setPower(30);
    const bundledCargo = await readCargo(); // read in cargo rfids
    // submit cargo
    submitActualCargo(bundledCargo).then((res) => {
      console.log(JSON.stringify(res));
      // TODO: train_mailbox should be set to either do_check_cargo again or do_victory_lap
      await emitTrainMailboxEvent('do_victory_lap');
      motor.setPower(-20); // move backwards to get function to reevaluate
    })
    .catch((error) => {
      console.error(error);
      await emitTrainMailboxEvent('do_check_cargo');
      motor.setPower(-20); // move backwards to get function to reevaluate
    });
    return;
  }
  
  if(trainMailbox.input === 'do_victory_lap') {
    if(goingOnVictoryLap) {
      motor.stop();
      clearTrainMailbox();
      console.log('Session success!');
      // TODO: reset whole game state
    } else {
      motor.setPower(50);
      goingOnVictoryLap = true;
      console.log('Going on victory lap!');
    }
    return;
  }
}

module.exports = { startGameLoop };
