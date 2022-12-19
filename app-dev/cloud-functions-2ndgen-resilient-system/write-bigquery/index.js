const functions = require("@google-cloud/functions-framework");
const { BigQuery } = require("@google-cloud/bigquery");
const bigquery = new BigQuery();
const { google } = require("googleapis");

// Register a CloudEvent callback with the Functions Framework that will
// be executed when the Pub/Sub trigger topic receives a message.
functions.cloudEvent("write-bigquery", async (cloudEvent) => {
  const record = JSON.parse(Buffer.from(cloudEvent.data.message.data, "base64").toString());

  try {
    await updateSheet(record.ts, "writeBigQuery", "Trying");
    await bigquery.dataset("sensor_data").table("readings").insert([record]);
    await updateSheet(record.ts, "writeBigQuery", "Success");
  } catch (ex) {
    await updateSheet(record.ts, "writeBigQuery", "Failure");
    throw new Error(ex);
  }
});

function decodePubSubMessage(message) {
  return JSON.parse(Buffer.from(message.data, "base64").toString());
}

const SHEET_ID = process.env.SHEET_ID;
let sheetsService;

async function updateSheet(ts, functionName, status) {
  if (!SHEET_ID) {
    console.warn("Warning: SHEET_ID not set to update ", functionName, status);
    return;
  }
  let row = await getRow(ts);
  if (row == -1) {
    row = await appendRow(ts);
  }
  col = functionName == "writeBigQuery" ? "C" : "B";
  await writeCell(row, col, status);
}

async function getRow(ts) {
  const sheetsService = await getSheetsService();
  const response = await sheetsService.spreadsheets.values.get({
    spreadsheetId: SHEET_ID,
    range: `Sheet1!A:A`
  });
  let timestamps = response.data.values.map((row) => row[0]);
  const row = timestamps.indexOf(ts.toString());
  if (row == -1) {
    return -1;
  } else {
    return row + 1; // Rows are one-based in the sheet.
  }
}

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

async function writeCell(row, col, status) {
  const values = [[status]];
  const resource = { values };
  await sheetsService.spreadsheets.values.update({
    spreadsheetId: SHEET_ID,
    range: `Sheet1!${col}${row}`,
    valueInputOption: "RAW",
    resource
  });
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
