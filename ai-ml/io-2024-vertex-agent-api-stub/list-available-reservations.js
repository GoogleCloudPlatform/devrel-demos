/*
 Copyright 2024 Google LLC

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

const functions = require('@google-cloud/functions-framework');

functions.http('listAvailableReservations', (req, res) => {
  parkName = req.parkName;
  requestedDate = req.requestedDate

  res.json([
    {
        "parkName": parkName,
        "reservationDateTime": "11:30:00"
    },
    {
        "parkName": parkName,
        "reservationDateTime": "12:30:00"
    },
    {
        "parkName": parkName,
        "reservationDateTime": "15:00:00"
    }
  ])
});
