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

const { initTrain } = require("./utils/train.js");
const { ports, parsers } = require("./utils/checkpoints.js");
const { poweredUP } = require("./utils/firebase.js");
const {
  readTrain,
  updateTrainMovement,
} = require("./utils/trainState.js");

const expressApp = express();
expressApp.use(express.json());
expressApp.use(express.static("express"));
expressApp.use(express.static("public"));

/**
 * listenToReaders
 * ----------------------
 * -> should update state of current train location
 * -> push up information to firestore
 */
function listenToReaders() {
  parsers[0].on("data", (chunk) => readTrain(chunk, 0));
  parsers[1].on("data", (chunk) => readTrain(chunk, 1));
  parsers[2].on("data", (chunk) => readTrain(chunk, 2));
  parsers[3].on("data", (chunk) => readTrain(chunk, 3));
}

/**
 * initialize
 */
(function initialize(useStubTrain = false) {
  !useStubTrain && initTrain();
  listenToReaders();
})();

/**
 * GET /stop
 */
expressApp.get("/stop", (req, res) => {
  console.log("Stopping train ...");
  updateTrainMovement(false);
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
expressApp.get("/start", (req, res) => {
  const urlParts = url.parse(req.url, true);
  const query = urlParts.query;

  const useStubTrain = query["train"] === "dummy";
  // Start train movment
  updateTrainMovement(true, 30);
  
  useStubTrain
    ? console.log("Starting dummy train ...")
    : console.log("Starting train ...");

  res.redirect(
    `/?message=${encodeURIComponent(useStubTrain ? "Starting dummy train" : "Starting train")}`,
  );
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
