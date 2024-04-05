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

const {
  clearTrainMailbox,
  trainMailboxListener,
  signalListener,
  proposalListener,
  updateInputMailbox,
  submitActualCargo,
} = require("./utils/firestoreHelpers.js");
const { getMotor } = require("./utils/train.js");
const { queueMessageToPublish } = require("./utils/metrics.js");

// Cargo reading
let beginReading = false;
let stockedCargo = [];

// Cargo results & Mailbox
let trainMailbox = {};
let proposalResult = {};

// Train movement states
let moveBackToStation = false;
let moveForwardsToStation = false;
let signalLights = {};
  
// Hardcoded rfid tag id to capture front car 
// and back car (to calculate middle cargo)
const frontCar = "\x03\x02330035AD1EB5\r";
const backCar = "\x03\x023300348E9019\r";

/**
 * Train mailbox listener
 */
trainMailboxListener(async (snapshot) => {
  trainMailbox = snapshot?.data() || {};
  trainMailbox && (await updateGameLoop());
});

/**
 * Signal listener
 * ----------------------
 */
signalListener(async(snapshot) => {
  const { one, two, three, four } = snapshot?.data() || {};
  signalLights?.["signal_1"](one?.target_state || 'off');
  signalLights?.["signal_2"](two?.target_state || 'off');
  signalLights?.["signal_3"](three?.target_state || 'off');
  signalLights?.["signal_4"](four?.target_state || 'off');
});

/**
 * Proposal listener
 * ----------------------
 */
proposalListener(async (snapshot) => {
  proposalResult = snapshot?.data()?.proposal_result || {};

  if (proposalResult) {
    const motor = await getMotor();
    if (trainMailbox?.input === "do_check_cargo") {
      // If cargo isn't valid, head back to station to reload cargo
      if (proposalResult?.reason && !proposalResult?.clear) {
        moveBackToStation = true;
        motor?.setPower(-30);
        queueMessageToPublish("cargo-reload", {stockedCargo});
        stockedCargo = [];
      }
    }
  }
});

/**
 * readCargo
 * ----------------------
 */
async function readCargo(chunk, role) {
  const motor = await getMotor();

  // In either cargo error & reload stage (backwards to station)
  // Or in victory lap mode (forwards to station)
  if (moveBackToStation || moveForwardsToStation) {
    await moveToStation(chunk, role);
    return;
  }

  const tagId = new String(chunk);
  const isFrontCar = frontCar.includes(tagId);
  const isBackCar = backCar.includes(tagId);
  const isCargo = !isFrontCar && !isBackCar;

  // MIDDLE: In the middle of train, store cargo chunk and continue on
  if (isCargo && beginReading) {
    stockedCargo.push(chunk);
  }
  // FRONT: Begin reading cargo
  if (isFrontCar) {
    beginReading = true;
  }
  // BACK: At tailend of train, wrap up and send read cargo to firestore
  if (isBackCar) {
    beginReading = false;
    motor?.brake();
    motor?.stop();

    try {
      // Submit held cargo
      await submitActualCargo(stockedCargo);
      queueMessageToPublish("cargo-read", {stockedCargo});
    } catch (error) {
      console.error(error);
    }
  }
}

/**
 * moveToStation
 * ----------------------
 * In either cargo error & reload stage (backwards to station)
 * Or in victory lap mode (forwards to station)
 */
async function moveToStation(chunk, role) {
  const tagId = new String(chunk);
  const motor = await getMotor();
  
  const isFrontCar = frontCar.includes(tagId);

  if (isFrontCar && role === "station") {
    motor?.brake();
    motor?.stop();
    moveBackToStation = false;
    moveForwardsToStation = false;
    return;
  }
  moveForwardsToStation && motor?.setPower(30);
  moveBackToStation && motor?.setPower(-40);
}

/**
 * updateGameLoop
 * ----------------------
 * Main game loop for train. Callback fn to all 
 * serialport / rfid readers so state is not held within loop
 */
async function updateGameLoop() {
  const motor = await getMotor();
  motor?.brake();
  motor?.stop();

  if (trainMailbox?.input === "do_check_cargo") {
    motor?.setPower(30);
    return;
  }

  if (trainMailbox?.input === "do_victory_lap") {
    if (moveForwardsToStation) {
      // Victory lap completed, now reset
      moveForwardsToStation = false;
      motor?.stop();
      // Reset train mailbox
      resetGameState();
      await clearTrainMailbox();
      console.log("Session success!");
      await updateInputMailbox("reset"); 
    } else {
      // Go on victory lap
      moveForwardsToStation = true;
      motor?.setPower(40);

      queueMessageToPublish("victory", {});
    }
  }
}


/**
 * changeSignalLight
 * ----------------------
 * "this" refers to opened serial
 * port & sends in one of three states
 * to Adafruit QTPy RP2040 signal.
 * ----------------------
 * clear (green led) - "cleared" to proceed
 * stop (red led) 
 * off (led should be off)
 *
 */ 
function changeSignalLight(state) {
  if(state === "clear" || state === "stop" || state === "off") {
    this?.write(`${state}\n`);
  }
}

/**
 * storeSignal
 * ----------------------
 * Stores function to change light states
 * that is binded to serial port reference
 */ 
async function storeSignal(role="", listener=()=>{}) {
  if(role !== "") {
    signalLights[role] = changeSignalLight.bind(listener);
  }
}

/**
 * resetGameState
 * ----------------------
 * Clears & resets global variables
 * and any other game states
 */ 
async function resetGameState() {
  signalLights = {};
  signalLightsUpdate = {};
  // Reset cargo reading
  beginReading = false;
  stockedCargo = [];
  // Reset cargo results & Mailbox
  trainMailbox = {};
  proposalResult = {};
  // Reset train movement states
  moveBackToStation = false;
  moveForwardsToStation = false;
}

module.exports = {
  readCargo,
  storeSignal,
  updateGameLoop,
  resetGameState
};
