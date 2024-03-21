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

const ControlPanel = (worldState, proposal, result) => {
  return (
    <div className="controlPanelContainer">
      <div className="controlPanelWrapper">
        <div className="controlPanel">
          <div className="worldState">
            World State:
            <p>{JSON.stringify(worldState)}</p>
          </div>
          <div className="proposal">
            Proposal:
            <p>{JSON.stringify(proposal)}</p>
          </div>
          <div className="proposalResult">
            Proposal Result:
            <p>{JSON.stringify(result)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ControlPanel;
