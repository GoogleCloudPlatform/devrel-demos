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

import React, { useState, useEffect } from "react";
import { useSelector, useDispatch } from "react-redux";
import Signal from "./Signal";
import { getPatterns } from "../actions/coreActions";
import SuccessState from "../assets/conductor-success.gif";
import TryAgainState from "../assets/conductor-try-again.gif";
import ExtrasQRCode from "../assets/qrcode-extras.png";
import { publishMessage } from "../utils/pubsub";
import "./styles/CargoResult.css";

/**
 * CargoResult
 * -----------------
 *
 */
const CargoResult = (props) => {
  const { proposal, signals, train } = props;
  const { pattern_slug, proposal_result } = proposal;
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(getPatterns());
  }, [dispatch]);

  const showSuccess = proposal_result?.clear && proposal_result?.reason;
  const showError = !proposal_result?.clear && proposal_result?.reason;

  useEffect(async () => {
    if (proposal_result?.reason) {
      await publishMessage("cargo_read", {
        result: proposal_result,
        timestamp: Date.now(),
      });
    }
    // Session complete!
    if (showSuccess) {
      await publishMessage("victory", {
        result: proposal_result,
        timestamp: Date.now(),
      });
    }
    // Wrong cargo
    if (showError) {
      await publishMessage("cargo_reload", {
        result: proposal_result,
        timestamp: Date.now(),
      });
    }
  }, [proposal_result]);

  const { patterns } = state.coreReducer;
  const selectedPattern = patterns?.filter((p) => p.slug === pattern_slug)?.[0];

  const results = proposal_result?.checkpoint_results;

  return selectedPattern?.checkpoints?.length === 0 ? (
    <h3>{"No checkpoints available."}</h3>
  ) : (
    <div className="cargoResultContainer">
      <p>
        <b>Goal: </b> {selectedPattern?.description}
      </p>
      {selectedPattern?.checkpoints?.map((step, index) => (
        <div className="stepWrapper">
          <div className="stepResults">
            <Signal
              trainLocation={train?.actual_location}
              signal={{
                target_state: results?.[index]?.clear ? "clear" : "stop",
              }}
              showTrainLocation={false}
            />
          </div>
          <div className="step">
            <b>{`Step ${index + 1}: `}</b>
            {step.description}
            <p
              className={
                results?.[index]?.clear ? "resultSuccess" : "resultError"
              }
            >
              <span>{results?.[index]?.clear}</span>
              <span>{results?.[index]?.reason}</span>
            </p>
          </div>
        </div>
      ))}
      {showError && (
        <div className="resultContainer">
          <h3>{"Oh no!"}</h3>
          <div className="tryAgainState">
            <img alt="try again" src={TryAgainState} />
          </div>
          <p>{proposal_result?.reason}</p>
        </div>
      )}
      {showSuccess && (
        <div className="resultContainer">
          <div className="successState">
            <img alt="success" src={SuccessState} />
          </div>
          <div>{"Huzzah!"}</div>
          <div>{proposal_result?.reason}</div>
          <img alt="Extras" src={ExtrasQRCode} className="qrcode" />
        </div>
      )}
    </div>
  );
};

export default CargoResult;
