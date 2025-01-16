# Beat Google at Load Balancing

Other/Internal Name:
* The Load Balancing Blitz
* Beat the Load Balancer 

## What is Beat Google at Load Balancing?

Beat Google at Load Balancing is a fun interactive educational game. In this 60
seconds game, the user is provided with 4 workers machines and Google Cloud Load
Balancer (GCLB) is provided with another 4 workers machines.

When the game start, simulated HTTP traffic flows towards the player and the GCLB.
Each HTTP request takes a fixed amout of CPU time adn each worker machine has limited
Queue capacity. Goal of the Player is to dispense the traffic load to worker machines
 and GCLB will automatically manage the web traffic while also doing necessary Health
checks to ensure its VM are health are fine.

Each request completed during the game duration, give 1 point. Player goal is make the
highest score and beat the GCLB.

## How to setup?

The Application code in set into 3 sections

1. Backend infrastructure: For more details check (/infra/README.md)[/infra/README.md]
1. Scoreboard: For more details check (/scoreboard/README.md)[/scoreboard/README.md]
1. Frontend: For more details check (/frontend/README.md)[/frontend/README.md]

## Architecture

(TODO)

## Licence

Apache Licence 2.0 - Copyright 2024 Google LLC
