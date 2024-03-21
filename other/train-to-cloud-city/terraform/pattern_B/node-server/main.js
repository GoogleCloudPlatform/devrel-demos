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

const {Firestore} = require('@google-cloud/firestore');

const firestore = new Firestore();

(async function quickstart() {
  const ref = firestore.collection("plants");
  let plants = [];
  
  try {
    const snapshot = await ref.get();
    snapshot.docs.forEach((doc) => {
      plants.push(doc.data());
    });
  } catch(error) {
    console.error(error);
  }
})();
