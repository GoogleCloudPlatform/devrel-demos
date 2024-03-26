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

const { firebase, db, app, firestore } = require("./firebase.js");
const { StringDecoder } = require("node:string_decoder");
const { getMotor } = require("./train.js");

/**
 * setMissionPattern (step 1)
 * ----------------------
 */ 
async function setMissionPattern(chunk, reader) {
  const motor = await getMotor();
  const matchingTag = await getMatchingTag({ chunk }); 
  const proposalRef = db.collection("global").doc("proposal");
  const mailboxRef = db.collection("global").doc("input_mailbox");
  
  /** 
   * PATTERNS TO SELECT FROM
   * high complex - 3300348D69E3
   * medium complex -  33003558732D
   * low complex - 0D0088F32B5D
   */
  if (matchingTag?.pattern_slug) {
    try {
      await proposalRef.set({ pattern_slug: matchingTag?.pattern_slug }, { merge: false });
      console.log(`Mission has been read: ${JSON.stringify(matchingTag?.pattern_slug)}. Waiting for event input trigger.`);
    } catch(error) {
      console.error(error);
    }
    return;
  }

  /** 
   * EVENT RFID TAG (let's go magic wand)
   * check_pattern - 0D00876E4DA9
   */
  if (matchingTag?.event_slug) {
    try {
      await mailboxRef.set({ input: "check_pattern"});
      motor.setPower(30); // move towards station
      console.log(`Input mailbox has been triggered to check pattern and now moving to station.`);
    } catch(error) {
      motor.stop();
      console.error(error);
    }
  }
}

/**
 * getProposalResult
 * ----------------------
 */
async function getProposalResult() {
  const proposalRef = db.collection("global").doc("proposal");
  let result = {};
  try {
    const snapshot = await proposalRef.get();
    const data = snapshot.data();
    result = data.result;
  } catch(error) {
    console.error(error);
  }

  return result;
}

/**
 * getMatchingTag
 * ----------------------
 *  Fetches GCP services, mission patterns, event tags (i.e eval trigger tag)
 */
async function getMatchingTag(id) {
  const tagRef = db.collection("tags");
  let tag = {};  
  try {
    const snapshot = await tagRef.get();
    snapshot.docs.forEach((doc) => {
      const data = doc.data();
      const chunk = new String(id?.chunk);
      const docId = new String(doc.id);
      if (chunk.includes(docId)) {
        tag = data;
      }
    });
  } catch(error) {
    console.error(error);
  }
  return tag;
}

/**
 * getTrain
 * ----------------------
 */
async function getTrain() {
  const trainRef = db.collection("global").doc("train");
  let doc = {};
  try {
    const snapshot = await trainRef.get();
    doc = snapshot.data();
  } catch(error) {
    console.error(error);
  }

  return doc;
}

/**
 * getTrainMailbox
 * ----------------------
 */
async function getTrainMailbox() {
  const trainRef = db.collection("global").doc("train_mailbox");
  let doc = {};

  try {
    const snapshot = await trainRef.get();
    doc = snapshot.data();
  } catch(error) {
    console.error(error);
  }

  return doc;
}

/**
 * clearTrainMailbox
 * ----------------------
 */
async function clearTrainMailbox() {
  const ref = db.collection("global").doc("train_mailbox");
  try {
    await ref.update({ input: null}, { merge: true });
    console.log(`Train mailbox cleared`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * matchCargoToServices
 *-------------------
 * chunks -> rfid tag id
 */
async function matchCargoToServices(chunks) {
  let cargos = [];

  for(const chunk of chunks) {
    const buffer = Buffer.from(JSON.stringify({ chunk }));
    const id = JSON.parse(buffer.toString());
    // Match read rfid chunk with correct service
    const matchingService = await getMatchingTag(id);

    if(matchingService?.slug) {
      cargos.push(matchingService.slug);
    }
  }

  return cargos;
}

/**
 * submitActualCargo
 *-------------------
 * chunks -> rfid tag id
 */
async function submitActualCargo(chunks) {
  let cargos = await matchCargoToServices(chunks);

  // Updates actual_cargo state with newly read service
  const ref = db.collection("global").doc("cargo");
  try {
    await ref.update({ actual_cargo: cargos }, { merge: true });
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
async function updateLocation(chunk, location) {
  const ref = db.collection("global").doc("train");
  try {
    const trainUpdate = {
      actual_location: location,
    }; 
    await ref.update(trainUpdate, { merge: true });
    console.log(`Passed checkpoint ${location}`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * updateInputMailbox
 *-------------------
 * index -> step train is on
 */
async function updateInputMailbox(chunk, location) {
  const ref = db.collection("global").doc("input_mailbox");
  try {
    await ref.update({ input: eventString }, { merge: true });
  } catch(error) {
    console.error(error);
  }
};

module.exports = {
  getTrain,
  getProposalResult,
  getTrainMailbox,
  setMissionPattern,
  updateLocation,
  updateInputMailbox,
  submitActualCargo,
  clearTrainMailbox,
};