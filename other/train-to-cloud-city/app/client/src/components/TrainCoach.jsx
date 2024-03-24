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

import React from "react";
import Car from "../assets/train-car.png";
import FrontCar from "../assets/train-engine.png";
import "./styles/TrainCoach.css";

/**
 * TrainCoach
 * -----------------
 *
 */
const TrainCoach = (props) => {
  const { name } = props;

  return (
    <div className="trainCoachContainer">
      <div className="trainCoachWrapper">
        <div className="coach">
          {name === "front" ? (
            <img alt="FrontCar" src={FrontCar} />
          ) : (
            <img alt="Car" src={Car} />
          )}
        </div>
      </div>
    </div>
  );
};

export default TrainCoach;
