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

const http = require("http");
const express = require("express");
const path = require("path");
const url = require("url");

const { initTrain, getMotor } = require("./utils/train.js");
const { getPorts } = require("./utils/checkpoints.js");
const { setMissionPattern, updateLocation, updateInputMailbox } = require("./utils/firestoreHelpers.js");
const { readCargo, updateGameLoop } = require("./trainGame.js");

const expressApp = express();
expressApp.use(express.json());
expressApp.use(express.static("express"));
expressApp.use(express.static("public"));

const { SerialPort, ReadlineParser } = require("serialport");

/**
 * listenToReaders (setup)
 * ----------------------
 * -> should update state of current train location
 * -> push up information to firestore
 */
async function listenToReaders() {
  const ports = await getPorts();
  
  ports?.forEach((port, index) => {
    const listener = (new SerialPort(port)).pipe(new ReadlineParser());
    // listeners are passed their location role (i.e station, checkpoint, etc);
    switch(port?.role) {
      case 'mission_check': {
        listener.on("data", (chunk) => setMissionPattern(chunk, port?.role));
      }
      case 'station': {
        listener.on("data", (chunk) => readCargo(chunk, port?.role));
      }
      default: {
        // TODO: isolate out so that other readers are just updating location (port.role)
        // listener.on("data", () => updateLocation(port?.role));
      }
    }
  });
}

/**
 * initialize
 */
(async function initialize() {
  initTrain();
  listenToReaders();
  await updateInputMailbox('reset');
})();

expressApp.get("/check-pattern", async (req, res) => {
  console.log("Check cargo ...");
});

/**
 * GET /stop
 */
expressApp.get("/stop", async (req, res) => {
  console.log("Stopping train ...");
  
  const motor = await getMotor();
  motor.stop();

  res.redirect(`/?message=${encodeURIComponent("Stopping train")}`);
});

/**
 * get /reset
 */
expressApp.get("/reset", async (req, res) => {
  console.log("Resetting train state ...");
  await updateInputMailbox('reset');
  res.redirect(`/?message=${encodeURIComponent("Resetting train")}`);
});

/**
 * GET /start
 */
expressApp.get("/start", async (req, res) => {
  const urlParts = url.parse(req.url, true);
  const query = urlParts.query;

  try { 
    console.log("Starting train demo ...");
    res.redirect(`/?message=${encodeURIComponent("Starting train")}`);
  } catch(error) {
    console.error(error);
  }

});

/**
 * GET /
 */
expressApp.get("/", (req, res) => {
  const urlParts = url.parse(req.url, true);
  const query = urlParts.query;

  res.sendFile(path.join(__dirname + "/public/index.html"));
});

expressApp.listen(3000, () => console.log("Listening to 3000"));
