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
import { useSelector, useDispatch } from "react-redux";
import ControlPanel from "./ControlPanel";
import QuizForm from "./QuizForm";
import Train from "./Train";
import Signal from "./Signal";
import Ribbon from "./Ribbon";
import { stopMission, resetMission } from "../actions/coreActions";
import "./styles/Dashboard.css";

/**
 * Dashboard
 * -----------------
 *
 */
const Dashboard = (props) => {
  const state = useSelector((state) => state);
  const dispatch = useDispatch();
  const { isSimulator, selectedPattern, proposal } = props;

  const showQuiz = !isSimulator;
  const { services,  worldState } = state.coreReducer;
  
  const { cargo, session_mailbox, signals, train, train_mailbox } =
    worldState;

  // Stop and reset whole mission
  const handleStopMission = (event) => {
    dispatch(stopMission());
    window.location.replace("/");
  };

  // Keeps selected mission/pattern
  // Removes previously selected cargo
  const handleResetMission = (event) => {
    dispatch(resetMission());
  };

  return (
    <div className="dashboardContainer">
      <div className="dashboardWrapper">
        {showQuiz && (
          <div className="dashboardPanel">
            <div className="missionTitle">
              <h3>{`Your Mission: ${proposal?.pattern_slug}`}</h3>
            </div>
            {selectedPattern && (
              <QuizForm services={services} selectedPattern={selectedPattern} />
            )}
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
          <ControlPanel proposalResult={proposal?.proposal_result} trainMailbox={train_mailbox} />
        </div>
      </div>
      <div className="actionPanel">
        <button className="stop" onClick={handleStopMission}>
          Stop Mission
        </button>
        <button className="reset" onClick={handleResetMission}>
          Reset Mission
        </button>
      </div>
      <Ribbon />
    </div>
  );
};

export default Dashboard;
