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

const { json } = require("express");
const express = require("express");
const router = express.Router();
const { isCacheAvailable } = require("./app.js");

const redisKeyCats = "cats";
const redisKeyDogs = "dogs";

module.exports = (redisClient) => {
  // Get votes for dogs are better :)
  router.get("/dogs", async (req, res) => {
    if (!isCacheAvailable()) {
      return res.json({ votes: undefined, error: "Redis unavailable" });
    }

    // get current votes from Redis
    let cachedResults = await redisClient.get(redisKeyDogs);

    // if cache is empty (no votes yet), set 0 in Redis
    if (!cachedResults) {
      cachedResults = 0;
      await redisClient.set(redisKeyDogs, 0);
    }

    // return current votes
    res.json({ votes: cachedResults });
  });

  router.post("/dogs", async (req, res) => {
    // if Redis is not available
    if (!isCacheAvailable()) {
      return res.json({ votes: undefined, error: "Redis unavailable" });
    }

    await redisClient.incr(redisKeyDogs);

    // return updated votes
    let newDogVotes = await redisClient.get(redisKeyDogs);
    res.json({ votes: newDogVotes });
  });

  // Get votes for cats
  router.get("/cats", async (req, res) => {
    if (!isCacheAvailable()) {
      return res.json({ votes: undefined, error: "Redis unavailable" });
    }

    // get current votes from Redis
    let cachedResults = await redisClient.get(redisKeyCats);

    // if cache is empty (no votes yet), set 0 in Redis
    if (!cachedResults) {
      cachedResults = 0;
      await redisClient.set(redisKeyCats, 0);
    }

    // return current votes
    res.json({ votes: cachedResults });
  });

  router.post("/cats", async (req, res) => {
    // if Redis is not available
    if (!isCacheAvailable()) {
      return res.json({ votes: undefined, error: "Redis unavailable" });
    }

    await redisClient.incr(redisKeyCats);

    // return updated votes
    let newCatVotes = await redisClient.get(redisKeyCats);
    res.json({ votes: newCatVotes });
  });

  router.get("/redisStatus", async (req, res) => {
    const redisStatus = isCacheAvailable();
    res.json({ status: redisStatus });
  });

  return router;
};
