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

import { cloudEvent, CloudEvent } from "@google-cloud/functions-framework";
import { StorageObjectData } from "@google/events/cloud/storage/v1/StorageObjectData";
import { ImageAnnotatorClient } from "@google-cloud/vision";
import { Firestore } from "@google-cloud/firestore";
import { createHmac } from "crypto";

// Create new API clients
const firestore = new Firestore();
const imageAnnotatorClient = new ImageAnnotatorClient();

// load secrets
const secret = process.env.SECRET_API_KEY || "local secret";

cloudEvent("index", async (cloudevent: CloudEvent<StorageObjectData>) => {
  console.log("---------------\nProcessing for ", cloudevent.subject, "\n---------------");

  if (!cloudevent.data) {
    throw "CloudEvent does not contain data."
  }

  const filePath = `${cloudevent.data.bucket}/${cloudevent.data.name}`;

  //Get labes for Image via the Vision API
  const [result] = await imageAnnotatorClient.labelDetection(`gs://${filePath}`);
  const labelValues = result.labelAnnotations?.flatMap((o) => o.description);

  //hash file name with secret
  const hashedFilePath = createHmac('sha256', secret)
    .update(filePath)
    .digest('hex');

  //Store with filePath as key
  await firestore
    .doc(`${cloudevent.data.bucket}/${hashedFilePath}`)
    .set({ name: cloudevent.data.name, labels: labelValues, updated: cloudevent.time })

  console.log(`Successfully stored ${cloudevent.data.name} to Firestore (${cloudevent.data.bucket}/${hashedFilePath})`)
});