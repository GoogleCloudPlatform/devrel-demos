# Cloud Next 2022 - Cloud Run Integrations talk demo code

This folder contains the demo code for Cloud Next 2022: [Blg203 How to build next-level web applications with Cloud Run](https://www.youtube.com/watch?v=SiFo7XZc534)

## Prerequisites

You will need to have redis running locally, [per these instructions](https://redis.io/docs/getting-started/installation/).

## How to run

1. `cd vuejs-webapp`
2. `npm run build`
3. `mv dist ../cats-xor-dogs-service`
4. `cd ../cats-xor-dogs-service`
5. `npm run dev`
6. Visit `http://localhost:8080` to vote for cats 🐱 xor dogs 🐶
