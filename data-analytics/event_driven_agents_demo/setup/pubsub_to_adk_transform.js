/**
 * Cymbal Bank Transform - Clean Version
 * 1. Unwraps BigQuery 'TO_JSON_STRING' double-encoding if present.
 * 2. Extracts user_id dynamically.
 * 3. Returns pure JSON payload with no extra context text.
 */
function pubsub_to_adk_transform(message, metadata) {
  var rawData = "";

  // --- STEP 1: DECODE RAW BYTES ---
  if (message.data) {
    try {
      rawData = new TextDecoder("utf-8").decode(message.data);
    } catch (e) {
      rawData = message.data;
    }
  }

  // --- STEP 2: NORMALIZE & EXTRACT ---
  var cleanObject = {};
  var detectedUser = "pubsub-trigger"; // Default

  try {
    var parsed = JSON.parse(rawData);

    // CHECK: Is this the BigQuery "Double Encoded" format? ({ "data": "string" })
    if (parsed.data && typeof parsed.data === 'string') {
      try {
        // UNWRAP IT: Parse the inner string to get the real data
        cleanObject = JSON.parse(parsed.data);
      } catch (innerErr) {
        // Inner wasn't JSON, revert to original
        cleanObject = parsed;
      }
    } else {
      // It was already clean
      cleanObject = parsed;
    }

    // EXTRACT: Get the user_id from the clean object
    if (cleanObject.user_id) {
      detectedUser = cleanObject.user_id;
    }

  } catch (e) {
    // Edge Case: Message wasn't JSON at all. Wrap it safely.
    cleanObject = { "text_content": rawData };
  }

  // --- STEP 3: CONSTRUCT PAYLOAD ---
  var apiPayload = {
    "input": {
      // Send the CLEAN object as a string. 
      // This ensures Python gets {"user_id": "123"...} not {"data": "..."}
      "message": JSON.stringify(cleanObject),
      "user_id": detectedUser
    }
  };

  return {
    data: JSON.stringify(apiPayload),
    attributes: message.attributes
  };
}