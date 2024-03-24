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
import TrainCoach from "./TrainCoach";
import { useSelector, useDispatch } from "react-redux";
import "./styles/Train.css";

/**
 * Train
 * -----------------
 *
 */
const Train = (props) => {
  const { train } = props;
  const { actual_cargo, reader, target_location, actual_location } =
    train || {};

  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  // TODO: revisit when global_simulation actual_cargo is updated
  let cargo = actual_cargo || [];

  if (typeof actual_cargo === "string") {
    cargo = actual_cargo?.split(",");
  }

  let cars = [];
  cargo.forEach((cargo, index) => cars.push(<TrainCoach key={index} />));

  const trainClasses = "train ".concat(actual_location || "station");

  return (
    <div className="trainContainer">
      <div className="cloudTrain"></div>
      <div className="container">
        <div className="content">
          <div className={`${trainClasses}`}>
            {cars?.map((c) => c)}
            <TrainCoach name="front" />
          </div>
          <div className="track"></div>
        </div>
      </div>
    </div>
  );
};

export default Train;
