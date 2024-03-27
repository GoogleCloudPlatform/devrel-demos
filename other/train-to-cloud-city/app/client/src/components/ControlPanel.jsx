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
import "./styles/ControlPanel.css";

const ControlPanel = (props) => {
  const { proposalResult, trainMailbox } = props;

  return (
    <div className="controlPanelContainer">
      <div className="controlPanelWrapper">
        <div className="controlPanel">
          <div className="sessionMailbox">
            <h3> Proposal Result: </h3>
            {proposalResult ? <p>{JSON.stringify(proposalResult?.reason)}</p> : 'Waiting to process cargo ...'}
          </div>
          <div className="trainMailbox">
            <h3> Train: </h3>
            {trainMailbox ? <p>{JSON.stringify(trainMailbox)}</p> : 'Waiting for train events ...'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
