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
  updateInputMailbox,
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
  const tagId = new String(chunk);
  
  const frontCar = '\x02330035AD1EB5\r';
  const backCar = '\x03\x023300348E9019\r';
  
  const isFrontCar = frontCar.includes(tagId);
  const isBackCar = backCar.includes(tagId);
  const isCargo = !isFrontCar && !isBackCar;

  // MIDDLE: In the middle of train, store cargo chunk and continue on
  if(isCargo && beginReading) {
    holdCargo.push(chunk);
    try {
      await updateLocation(chunk, role);
    } catch(error) {
      console.error(error);
    }
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
  }

  return { isBackCar, holdCargo };
}


/**
 * startGameLoop
 * ----------------------
 * Main game loop for train. Callback fn to all serialport / rfid readers
 * so state is not held within loop, but above (TODO: refactor later)
 */ 
async function startGameLoop(chunk, checkpoint, role) {  
  if(role !== 'station') return;

  const motor = await getMotor();
  const trainMailbox = await getTrainMailbox();
  
  motor.stop();

  if(trainMailbox.input === 'do_check_cargo') {
    motor.setPower(30);
    let cargoResult = {
      isBackCar: false,
      holdCargo: []
    };
  
    if(cargoResult.isBackCar) {
      console.log(' reading completed, submit cargo');
      motor.stop();
      try {
        const result = await submitActualCargo(cargoResult.holdCargo);
      } catch (error) {
        console.error(error);
      }
    } else {
      const result = await readCargo(chunk, checkpoint, role); // read in cargo rfids
      cargoResult = result;
    }
    return;
  }
  
  if(trainMailbox.input === 'do_victory_lap') {
    if(goingOnVictoryLap) {
      motor.stop();
      // Reset train mailbox
      await clearTrainMailbox();
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
