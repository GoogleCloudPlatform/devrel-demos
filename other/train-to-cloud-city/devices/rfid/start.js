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
const { setMissionPattern } = require("./utils/firestoreHelpers.js");
const { evaluateRfidTags } = require("./trainGame.js");

const expressApp = express();
expressApp.use(express.json());
expressApp.use(express.static("express"));
expressApp.use(express.static("public"));

const { SerialPort, ReadlineParser } = require("serialport");

/**
 * listenToReaders
 * ----------------------
 * -> should update state of current train location
 * -> push up information to firestore
 */
async function listenToReaders() {
  const ports = await getPorts();
  
  ports?.forEach((port, index) => {
    const listener = (new SerialPort(port)).pipe(new ReadlineParser());
    // listeners are passed their location role (i.e station, checkpoint, etc);
    if(port?.role === 'mission_check') {
      listener.on("data", (chunk) => setMissionPattern(chunk, port?.role));
    } else {
      listener.on("data", (chunk) => evaluateRfidTags(chunk, index, port?.role));
    }
  });
}

/**
 * initialize
 */
(function initialize(useStubTrain = false) {
  !useStubTrain && initTrain();
  listenToReaders();
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
  motor.brake();
  motor.setPower(0);
  motor.stop();

  res.redirect(`/?message=${encodeURIComponent("Stopping train")}`);
});

/**
 * get /reset
 */
expressApp.get("/reset", (req, res) => {
  console.log("Resetting train state ...");
  // TODO: Move train to station
  res.redirect(`/?message=${encodeURIComponent("Resetting train")}`);
});

/**
 * GET /start
 */
expressApp.get("/start", async (req, res) => {
  const urlParts = url.parse(req.url, true);
  const query = urlParts.query;

  try { 
    const motor = await getMotor();
    motor.setPower(30);
    console.log("Starting train ...");
    res.redirect(
      `/?message=${encodeURIComponent(useStubTrain ? "Starting dummy train" : "Starting train")}`,
    );
  } catch(error) {
    res.status(400).send("Error: You must start the train first before starting");
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
