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
];

// Parsers
const parsers = [
  ports[0].pipe(new ReadlineParser()),
  ports[1].pipe(new ReadlineParser()),
  ports[2].pipe(new ReadlineParser()),
  ports[3].pipe(new ReadlineParser()),
];

module.exports = { ports, parsers };
