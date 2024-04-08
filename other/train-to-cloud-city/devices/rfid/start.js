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
const {
  setMissionPattern,
  updateLocation,
  updateInputMailbox,
} = require("./utils/firestoreHelpers.js");
const {
  readCargo,
  resetGameState,
  updateGameLoop,
  storeSignal,
} = require("./trainGame.js");

require("./utils/metrics.js");

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
    // listeners are passed their location role (i.e station, checkpoint, etc);
    if (port?.role === "mission_check") {
      const listener = new SerialPort(port).pipe(new ReadlineParser());
      listener.on("data", (chunk) => setMissionPattern(chunk, port?.role));
      return;
    }

    if (port?.role === "station") {
      const listener = new SerialPort(port).pipe(new ReadlineParser());
      listener.on("data", (chunk) => readCargo(chunk, port?.role));
      return;
    }

    if (port?.role.indexOf("checkpoint") > -1) {
      const listener = new SerialPort(port).pipe(new ReadlineParser());
      listener.on("data", () => updateLocation(port?.role));
      return;
    }

    if (port?.role.indexOf("signal") > -1) {
      const listener = new SerialPort(port);
      storeSignal(listener?.settings?.role, listener);
    }
  });
}

/**
 * initialize
 */
(async function initialize() {
  initTrain();
  listenToReaders();
  await updateInputMailbox("reset");
})();

/**
 * GET /stop
 */
expressApp.get("/stop", async (req, res) => {
  console.log("Stopping train ...");

  try {
    const motor = await getMotor();
    motor.stop();
  } catch (error) {
    res.send(`/?message=${encodeURIComponent("Stopping train")}`);
    res.status(400).json({ error });
  }
});

/**
 * get /reset
 */
expressApp.get("/reset", async (req, res) => {
  console.log("Resetting train state ...");

  try {
    resetGameState();
    await updateInputMailbox("reset");
    res
      .status(200)
      .redirect(`/?message=${encodeURIComponent("Resetting train")}`);
  } catch (error) {
    console.error(error);
    res.status(400).json({ error });
  }
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
    console.log("Starting train demo ...");
    res
      .status(200)
      .redirect(`/?message=${encodeURIComponent("Starting train")}`);
  } catch (error) {
    console.error(error);
    res.status(400).json({ error });
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

async function gracefulExit() {
  console.log("Caught interrupt signal. Resetting the game.");
  try {
    await updateInputMailbox("reset");
    console.log("Reset completed, exiting out.");
  } catch (error) {
    console.log(error);
  }
  process.exit(0);
}

// Attempt graceful exit if ctrl-c or unexpected crash
[`exit`, `SIGINT`, `uncaughtException`, `SIGTERM`].forEach((eventType) =>
  process.on(eventType, gracefulExit),
);

expressApp.listen(3000, () => console.log("Listening to 3000"));
