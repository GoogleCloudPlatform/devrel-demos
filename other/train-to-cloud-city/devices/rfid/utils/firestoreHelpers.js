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
const { getMotor } = require("./utils/train.js");

/**
 * setMissionPattern (step 1)
 * ----------------------
 * high complex - 3300348D69E3
 * medium complex -  33003558732D
 * low complex - 0D0088F32B5D
 *
 * TODO: step 1a train_mailbox updated to check_cargo?
 */ 
async function setMissionPattern(chunk, reader) {
  const motor = await getMotor();
  const mission = await getMatchingTag({ chunk });
  const ref = db.collection("global").doc("proposal");
  
  try {
    await ref.update({ pattern_slug: mission }, { merge: true });
    motor.setPower(30); // move towards station
    console.log(`Mission has been read: ${JSON.stringify(mission)} and now moving to station`);
  } catch(error) {
    motor.stop();
    console.error(error);
  }
}

/**
 * getMatchingTag
 * ----------------------
 */
async function getMatchingTag(id) {
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
 * getTrain
 * ----------------------
 */
async function getTrain() {
  const trainRef = db.collection("global").doc("train");
  let docs = [];
  try {
    const snapshot = await trainRef.get();
    doc = snapshot.data();
  } catch(error) {
    console.error(error);
  }

  return docs;
}
/**
 * getSessionMailbox
 * ----------------------
 */
async function getSessionMailbox() {
  const ref = db.collection("global").doc("session_mailbox");
  let docs = [];
  try {
    const snapshot = await ref.get();
    doc = snapshot.data();
  } catch(error) {
    console.error(error);
  }

  return docs;
}

/**
 * getTrainMailbox
 * ----------------------
 */
async function getTrainMailbox() {
  const trainRef = db.collection("global").doc("train_mailbox");
  let docs = [];
  try {
    const snapshot = await trainRef.get();
    doc = snapshot.data();
  } catch(error) {
    console.error(error);
  }

  return docs;
}

/**
 * clearTrainMailbox
 * ----------------------
 */
async function clearTrainMailbox() {
  const trainRef = db.collection("global").doc("train_mailbox");
  try {
    await ref.update({ input: null}, { merge: false });
    console.log(`Train mailbox cleared`);
  } catch(error) {
    console.error(error);
  }
}

/**
 * submitActualCargo
 *-------------------
 * chunks -> rfid tag id
 */
async function submitActualCargo(chunks) {
  let cargos = [];

  chunks?.forEach(async chunk => {
    const buffer = Buffer.from(JSON.stringify({ chunk }));
    const id = JSON.parse(buffer.toString());
    // Match read rfid chunk with correct service
    const matchingService = await getMatchingTag(id);
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
 * -----------------
 * proposalResult
 * -----------------
 */
const proposalResultUpdated = (async () => {
  const ref = db.collection("global").doc("proposal");
  await ref.onSnapshot(docSnapshot => {
    console.log(`Received doc snapshot:`);
    console.log(docSnapshot.data());  
  }, err => {
    console.log(`Encountered error: ${err}`);
  });

})();

/**
 * -----------------
 * trainMailboxUpdated
 * -----------------
 */
const trainMailboxUpdated = (async () => {
  const ref = db.collection("global").doc("train_mailbox");
  await ref.onSnapshot(docSnapshot => {
    console.log(`Train received doc snapshot:`);
    console.log(docSnapshot.data());  
  }, err => {
    console.log(`Encountered error: ${err}`);
  });
})();

/**
 * -----------------
 * sessionMailboxUpdated
 * -----------------
 */
const sessionMailboxUpdated = (async () => {
  const ref = db.collection("global").doc("session_mailbox");
  await ref.onSnapshot(docSnapshot => {
    console.log(`Session received doc snapshot:`);
    console.log(docSnapshot.data());  
  }, err => {
    console.log(`Encountered error: ${err}`);
  });
})();


module.exports = {
  getTrain,
  setMissionPattern,
  updateLocation,
  submitActualCargo,
  proposalResultUpdated,
  clearTrainMailbox,
  getTrainMailbox,
  getSessionMailbox,
  trainMailboxUpdated,
  sessionMailboxUpdated
};
