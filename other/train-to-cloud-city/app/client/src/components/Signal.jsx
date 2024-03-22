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
import Station from "../assets/Station.png";
import "./styles/Signal.css";

/**
 * Signal
 * -----------------
 *
 */
const Signal = (props) => {
  const { isStation, trainLocation, signal } = props;
  const { name, slug, actual_state, target_state } = signal || {};
  const position = isStation ? "station" : slug;
  const checkpointClasses = slug === "four" ? "circle" : "circle connector";
  const locationClasses =
    trainLocation === position
      ? checkpointClasses.concat(" here")
      : checkpointClasses;

  const redLightClasses =
    actual_state === "stop"
      ? "light red on"
      : target_state === "stop"
        ? "light red blinking"
        : "light red";
  const greenLightClasses =
    actual_state === "clear"
      ? "light green on"
      : target_state === "clear"
        ? "light green blinking"
        : "light green";

  return (
    <div className="signalContainer">
      <div className={locationClasses}></div>
      {isStation ? (
        <div className="stationCheckpoint">
          <img alt="Station" src={Station} />
        </div>
      ) : (
        <div className="signal">
          <div className={redLightClasses}></div>
          <div className={greenLightClasses}></div>
          <div className={"light yellow"}></div>
        </div>
      )}
    </div>
  );
};

export default Signal;
