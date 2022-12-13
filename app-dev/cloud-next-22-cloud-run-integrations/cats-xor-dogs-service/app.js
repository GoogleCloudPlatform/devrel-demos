/* Copyright 2022 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License. */

const express = require("express");
const app = express();
const port = 8080;

const redis = require("redis");
const REDISHOST = process.env.REDISHOST || "127.0.0.1";
const REDISPORT = process.env.REDISPORT || "6379";
const redisUrl = `redis://${REDISHOST}:${REDISPORT}`;
console.log(`using redisURL: redis://${REDISHOST}:${REDISPORT}`);

exports.isCacheAvailable = () => {
  return isRedisCacheAvailable;
};

let isRedisCacheAvailable;
let redisClient;
(async () => {
  redisClient = redis.createClient({
    url: redisUrl,
    socket: {
      reconnectStrategy: (retries) => Error("Don't retry")
    }
  });

  redisClient.on("error", (error) => {
    console.log("redis unavailable");
    isRedisCacheAvailable = false;
  });

  try {
    await redisClient.connect();
    isRedisCacheAvailable = true;
  } catch (error) {
    console.log("unable to start redis");
    isRedisCacheAvailable = false;
  }
})();

const routes = require("./routes");

app.use("/", routes(redisClient));

app.use(express.static("dist"));

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`);
});
