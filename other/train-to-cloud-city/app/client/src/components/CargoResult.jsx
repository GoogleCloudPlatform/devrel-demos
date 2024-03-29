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
import { getPatterns } from "../actions/coreActions";
import SuccessState from "../assets/conductor-success.gif";
import TryAgainState from "../assets/conductor-try-again.gif";
import ExtrasQRCode from "../assets/qrcode-extras.png";
import "./styles/CargoResult.css";

/**
 * CargoResult
 * -----------------
 *
 */
const CargoResult = (props) => {
  const { proposal } = props;
  const { pattern_slug, proposal_result } = proposal;
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  useEffect(() => {
    dispatch(getPatterns());
  }, [dispatch]);

  const { patterns } = state.coreReducer;
  const selectedPattern = (patterns?.filter(p => p.slug === pattern_slug))?.[0]; 
  
  const showSuccess = proposal_result?.clear && proposal_result?.reason;
  const showError = !proposal_result?.clear && proposal_result?.reason;


  return selectedPattern?.checkpoints?.length === 0 ? (
    <h3>{'No checkpoints available.'}</h3>
  ) : (
    <div className="missionForm">
      <p><b>Goal: </b> {selectedPattern?.description}</p>
      {selectedPattern?.checkpoints?.map((step, index) => (
        <p>
          <b>{`Step ${index + 1}: `}</b>
          {step.description}
        </p>
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
