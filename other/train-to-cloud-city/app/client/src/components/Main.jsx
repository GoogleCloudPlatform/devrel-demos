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

import React, { useEffect, useState } from "react";
import { useSelector, useDispatch } from "react-redux";
import Dashboard from "./Dashboard";
import {
  getWorldState,
  getPatterns,
  getServices,
  signalsUpdated,
  cargoUpdated,
  trainUpdated,
  trainMailboxUpdated,
  updateInputMailbox,
  proposalUpdated,
} from "../actions/coreActions";
import ConductorWave from "../assets/conductor-wave.gif";
import "./styles/Main.css";

/**
 * Main
 * -----------------
 * Sets environment and data to populate into dashboard
 * which is in 3 different states (simulator, realtime from physical train)
 */
const Main = (props) => {
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  const [toggled, setToggle] = useState(false);
  const [simulator, setSimulator] = useState(false);

  const [signals, setSignals] = useState({});
  const [cargo, setCargo] = useState({});
  const [train, setTrain] = useState({});
  const [proposal, setProposal] = useState({});
  const [trainMailbox, setTrainMailbox] = useState({});

  useEffect(() => {
    const cleanSlate = async() => {
      try {
        await updateInputMailbox("reset");
        Promise.all([dispatch(getServices()), dispatch(getPatterns())]);
      } catch (error) {
        console.log(error);
      }
    };
    
    const collection = simulator ? "global_simulation" : "global";
    // Listen for when patterns are updated
    proposalUpdated((data) => {
      setToggle(!!data.pattern_slug);
      if (!!data.pattern_slug) {
        setProposal(data);
      } else {
        setProposal({});
        cleanSlate();
      }
    }, collection);
    
    signalsUpdated((data) => setSignals(data), collection);
    trainUpdated((data) => setTrain(data), collection);
    cargoUpdated((data) => setCargo(data), collection);
    trainMailboxUpdated((data) => setTrainMailbox(data), collection);
  }, [simulator, dispatch]);

  const handleSimulator = async (event) => {
    setToggle(!simulator);
    setSimulator(!simulator);
    dispatch?.(getWorldState(simulator ? "global_simulation" : "global"));
  };

  return (
    <div className="mainContainer">
      <div className="mainWrapper">
        {proposal && !proposal.pattern_slug && (
          <div className="mainHeader">
            <div className="welcomeImage">
              <img alt="welcome-wave" src={ConductorWave} />
            </div>
            <div className="mainContent">
              <h2>Choose your adventure</h2>
              <p>
                Pick a mission wand and wave it over the center RFID reader to
                select!
              </p>
              <div className="section">
                {state.coreReducer.patterns?.map((pattern, index) => (
                  <div className="buttonStyle" key={index}>
                    <b>{pattern.name}</b>
                    <br />({` ${pattern.complexity.split("_").join(" ")}`})
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
        {toggled ? (
          <Dashboard
            proposal={proposal}
            train={train}
            cargo={cargo}
            signals={signals}
            trainMailbox={trainMailbox}
          />
        ) : (
          <a href="#" onClick={handleSimulator}>{"Turn on simulator"}</a>
        )}
      </div>
    </div>
  );
};

export default Main;
