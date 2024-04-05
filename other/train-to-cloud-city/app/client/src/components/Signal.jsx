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
import Station from "../assets/station.png";
import SignalGreen from "../assets/signal-green.svg";
import SignalOff from "../assets/signal-off.svg";
import SignalRed from "../assets/signal-red.svg";
import "./styles/Signal.css";

/**
 * Signal
 * -----------------
 *
 */
const Signal = (props) => {
  const { isStation, trainLocation, signal, showTrainLocation = true } = props;
  const { slug, target_state } = signal || {};
  const position = isStation ? "station" : slug;
  const checkpointClasses = slug === "four" ? "circle" : "circle connector";
  const locationClasses =
    trainLocation === position
      ? checkpointClasses.concat(" here")
      : checkpointClasses;

  let signalLight;
  switch (target_state) {
    case "stop": {
      signalLight = <img alt="SignalRed" src={SignalRed} />;
      break;
    }
    case "clear": {
      signalLight = <img alt="SignalGreen" src={SignalGreen} />;
      break;
    }
    default: {
      signalLight = <img alt="SignalOff" src={SignalOff} />;
    }
  }

  return (
    <div className="signalContainer">
      <div className={`signal ${position}`}>
        {isStation ? <img alt="Station" src={Station} /> : signalLight}
      </div>
      {showTrainLocation && <div className={locationClasses}></div>}
    </div>
  );
};

export default Signal;
