/*
 Copyright 2022 Google LLC
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at
      http://www.apache.org/licenses/LICENSE-2.0
 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*/

const functions = require("@google-cloud/functions-framework");
const { PubSub } = require("@google-cloud/pubsub");
const pubsub = new PubSub();
const { google } = require("googleapis");

const SHEET_ID = process.env.SHEET_ID;
let sheetsService;

// postTemperature HTTP function.
functions.http("post-temperature", async (req, res) => {
  const reading = req.body;
  reading.ts = Date.now();
  console.log(JSON.stringify(reading));
  await appendRow(reading.ts);
  const buffer = Buffer.from(JSON.stringify(reading));
  await pubsub.topic("readings").publish(buffer);
  res.send("OK\n");
});

async function appendRow(ts) {
  const sheetsService = await getSheetsService();
  const values = [[ts]];
  const resource = { values };
  const response = await sheetsService.spreadsheets.values.append({
    spreadsheetId: SHEET_ID,
    range: `Sheet1!A:A`,
    valueInputOption: "RAW",
    insertDataOption: "INSERT_ROWS",
    resource: resource
  });
  const updatedCell = response.data.updates.updatedRange;
  const match = updatedCell.match("A(\\d+)");
  if (match) {
    return match[1];
  }
  return -1;
}

async function getSheetsService() {
  if (!sheetsService) {
    const auth = await google.auth.getClient({
      scopes: ["https://www.googleapis.com/auth/spreadsheets"]
    });
    sheetsService = google.sheets({ version: "v4", auth });
  }
  return sheetsService;
}
