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
import { useSelector } from "react-redux";
import ControlPanel from "./ControlPanel";
import QuizForm from "./QuizForm";
import Train from "./Train";
import Signal from "./Signal";
import Ribbon from "./Ribbon";
import "./styles/Dashboard.css";

/**
 * Dashboard
 * -----------------
 *
 */
const Dashboard = (props) => {
  const state = useSelector((state) => state);
  const { isSimulator } = props;
  const { services, selectedPattern, worldState } = state.coreReducer;
  const { cargo, proposal, session_mailbox, signals, train, train_mailbox } = worldState;

  return (
    <div className="dashboardContainer">
      <div className="dashboardWrapper">
        {!isSimulator && (
          <div className="dashboardPanel">
            <div className="missionTitle">
              <h3>{`Your Mission: ${selectedPattern?.name}`}</h3>
            </div>
            {selectedPattern && <QuizForm services={services} selectedPattern={selectedPattern} />}
          </div>
        )}
        <div className="dashboardPanel">
          <div className="dashboardSignals">
            <div className="columns">
              <p>Loaded cargo ...</p>
              <Signal isStation={true} trainLocation={train?.actual_location} />
              <Signal
                trainLocation={train?.actual_location}
                signal={signals?.one}
              />
              <Signal
                trainLocation={train?.actual_location}
                signal={signals?.two}
              />
              <Signal
                trainLocation={train?.actual_location}
                signal={signals?.three}
              />
              <Signal
                trainLocation={train?.actual_location}
                signal={signals?.four}
              />
            </div>
          </div>
          <Train train={train} />
          <ControlPanel worldState={worldState} />
        </div>
      </div>
      <Ribbon />
    </div>
  );
};

export default Dashboard;
