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

const { db, app, firestore } = require("./firebase.js");
const PoweredUP = require("node-poweredup");
const poweredUP = new PoweredUP.PoweredUP();

/**
 * initTrain
 */
function initTrain() {
  poweredUP?.on("discover", async (hub) => {
    console.log(`Discovered ${hub.name}!`);
    hub?.connect();
    console.log("Connected");
  });
  poweredUP.scan(); // Start scanning for Hubs
  console.log("Scanning for Hubs...");
}

async function getMotor() {
  const hubs = poweredUP?.getHubs();
  let motor;
  try {
    motor = await hubs[0]?.waitForDeviceAtPort("A");
  } catch (error) {
    console.log(error);
  }
  return motor;
}

module.exports = { initTrain, poweredUP, getMotor };
