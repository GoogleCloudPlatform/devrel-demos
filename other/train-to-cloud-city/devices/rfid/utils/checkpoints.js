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

const { SerialPort, ReadlineParser } = require("serialport");

// Train checkpoints
const ports = [
  new SerialPort({
    path: "/dev/ttyUSB0",
    baudRate: 9600,
  }),
  new SerialPort({
    path: "/dev/ttyUSB1",
    baudRate: 9600,
  }),
  new SerialPort({
    path: "/dev/ttyUSB2",
    baudRate: 9600,
  }),
  new SerialPort({
    path: "/dev/ttyUSB3",
    baudRate: 9600,
  }),
  new SerialPort({
    path: "/dev/ttyUSB4",
    baudRate: 9600,
  }),
  new SerialPort({
    path: "/dev/ttyUSB5",
    baudRate: 9600,
  }),
];

const roles = [
  { location: "station", serialNumber: "A10LXV9Y" },
  { location: "checkpoint_1", serialNumber: "A10LXV95" },
  { location: "checkpoint_2", serialNumber: "A10LXVA5" },
  { location: "checkpoint_3", serialNumber: "A10LY36P" },
  { location: "checkpoint_4", serialNumber: "A10LY36T" },
  { location: "mission_check", serialNumber: "A10LXV9L" },
];

const mappedRfidRoles = async function() {
  let mapped = [];
  try {
    const ports = await SerialPort.list();
    ports.forEach((port, index) => {
      let matches = roles.filter(role => port.serialNumber === role.serialNumber);
      matches[0] && mapped.push({ ...matches[0], ...port });
    });
  } catch(error) {
    console.error(error);
  }

  console.log(mapped);

  return mapped;
};

// Parsers
const parsers = [
  ports[0].pipe(new ReadlineParser()),
  ports[1].pipe(new ReadlineParser()),
  ports[2].pipe(new ReadlineParser()),
  ports[3].pipe(new ReadlineParser()),
  ports[4].pipe(new ReadlineParser()),
  ports[5].pipe(new ReadlineParser()),
];

module.exports = { ports, parsers, roles, mappedRfidRoles };
