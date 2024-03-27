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
  getProposalResult,
  clearTrainMailbox,
  trainMailboxListener,
  proposalListener,
  updateInputMailbox,
  validateCargo,
  updateLocation,
  submitActualCargo
} = require("./utils/firestoreHelpers.js");
const { getMotor } = require("./utils/train.js");

// Cargo reading
let beginReading = false;
let stockedCargo = [];

// Mailbox
let trainMailbox = {};

let proposalResult = {};

// Train movement states
let moveBackToStation = false;
let moveForwardsToStation = false;

// Train mailbox listener
trainMailboxListener(async snapshot => {
  const motor = await getMotor();
  trainMailbox = snapshot?.data();
  
  await updateGameLoop(null, null, 'station');
  //motor?.setPower(40);
});

/**
 * Proposal listener
 */ 
proposalListener(async snapshot => {
  const motor = await getMotor();
  proposalResult = snapshot?.data()?.proposal_result;
  
  if(trainMailbox?.input === 'do_check_cargo') {   
    // If cargo isn't valid
    // Head back to station to reload cargo
    if(proposalResult?.reason && !proposalResult?.clear) {
      moveBackToStation = true;
      motor?.setPower(-30);
      // reset
      await updateInputMailbox('reset');
    }
  }
});

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
    stockedCargo.push(chunk);
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

  return { isFrontCar, isBackCar };
}

/**
 * moveToStation
 * ----------------------
 * In either cargo error & reload stage (backwards to station)
 * Or in victory lap mode (forwards to station)
 */
async function moveToStation(chunk, role) {
  const tagId = new String(chunk);
  const frontCar = '\x03\x02330035AD1EB5\r';
  const isFrontCar = frontCar.includes(tagId); 
  const motor = await getMotor();

  if(isFrontCar && role === 'station') {
    motor?.brake();
    motor?.stop();
    moveBackToStation = false;
    moveForwardsToStation = false;
    return;
  } 
    
  moveForwardsToStation && motor?.setPower(35);
  moveBackToStation && motor?.setPower(-40);
}

/**
 * updateGameLoop
 * ----------------------
 * Main game loop for train. Callback fn to all serialport / rfid readers
 * so state is not held within loop, but above (TODO: refactor later)
 */ 
async function updateGameLoop(chunk, checkpoint, role) {  
  //if(role !== 'station') return;
  // In either cargo error & reload stage (backwards to station)
  // Or in victory lap mode (forwards to station)
  if (moveBackToStation || moveForwardsToStation) {
    await moveToStation(chunk, role);
    return;
  }

  const motor = await getMotor();
  motor?.brake();
  motor?.stop();

  if(trainMailbox?.input === 'do_check_cargo') {
    motor?.setPower(35);  
    // read in cargo rfids
    const { isBackCar } = await readCargo(chunk, checkpoint, role);
    if(isBackCar) {
      motor?.brake();
      motor?.stop();

      try {
        // Submit held cargo
        await submitActualCargo(stockedCargo); 
        stockedCargo = [];
      } catch (error) {
        console.error(error);
      }
    }
    return;
  }
  
  if(trainMailbox?.input === 'do_victory_lap') {
    if(moveForwardsToStation) {
      moveForwardsToStation = false; // reset
      motor?.stop();
      // Reset train mailbox
      await clearTrainMailbox();
      // TODO: Send metrics
      console.log('Session success!');
      // reset
      await updateInputMailbox('reset');
    } else {
      moveForwardsToStation = true;
      motor?.setPower(50);
      console.log('Going on victory lap!');
    }
  }
}

module.exports = { updateGameLoop };
