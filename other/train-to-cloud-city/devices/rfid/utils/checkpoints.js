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

const { SerialPort } = require("serialport");

const roles = {
  A10LXV9L: "mission_check",
  A10LXV9Y: "station",
  A10LXV95: "checkpoint_1",
  A10LXVA5: "checkpoint_2",
  A10LY36P: "checkpoint_3",
  A10LY36T: "checkpoint_4",
};

// Train checkpoints
const getPorts = async function () {
  let ports = [];
  try {
    const list = await SerialPort.list();
    list.forEach((port, index) => {
      const role = roles[port.serialNumber];
      if (role) {
        ports.push({
          role,
          path: port.path,
          serialNumber: port.serialNumber,
          baudRate: 9600,
        });
      }
    });
  } catch (error) {
    console.error(error);
  }
  return ports;
};

module.exports = { getPorts };
