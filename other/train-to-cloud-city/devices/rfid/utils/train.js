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
const { getTrainMovement } = require("./trainState.js");
const PoweredUP = require("node-poweredup");
const poweredUP = new PoweredUP.PoweredUP();

/**
 * initTrain
 */
function initTrain() {
  poweredUP?.on("discover", async (hub) => {
    console.log(`Discovered ${hub.name}!`);
    hub.connect();

    const motorA = await hub.waitForDeviceAtPort("A");
    console.log("Connected");

    // Main controller of the train,
    // checkpoints may manipulate the firestore train state
    // which is constantly checked on a loop
    while (true) {
      const { isRunning, power } = await getTrainMovement();
      // TODO: Try swapping onSnapshot listener rather than while(true)
      // to react only when the train collection is updated

      if (isRunning) {
        motorA.setPower(power || 30);
      } else {
        console.log('STOPPPP');
        motorA.brake();
        motorA.setPower(0);
        motorA.stop();
        await hub.sleep(3000);
      }
    }
  });
  poweredUP.scan(); // Start scanning for Hubs

  console.log("Scanning for Hubs...");
}

module.exports = { initTrain, poweredUP };
