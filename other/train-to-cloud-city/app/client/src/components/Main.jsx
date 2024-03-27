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
import ToggleButton from "./ToggleButton";
import {
  getWorld,
  getPatterns,
  getServices,
  trainMailboxUpdated,
  updateInputMailbox,
  proposalUpdated
} from "../actions/coreActions";
import "./styles/Main.css";

/**
 * Main
 * -----------------
 * Sets environment and data to populate into dashboard
 * which is in 3 different states (simulator, realtime, virtual input)
 */
const Main = (props) => {
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  const [adminView, setAdminView] = useState(false);
  const [toggled, setToggle] = useState(false);
  const [simulator, setSimulator] = useState(false);
  const [pattern, setPattern] = useState({});
  const [proposal, setProposal] = useState({});
    
  const handleSimulator = async (event) => {
    setToggle(event.target.checked);
    setSimulator(event.target.checked);
    await getWorld({
      dispatch,
      isSimulator: event.target.checked,
    });
  };
  
  const handlePatternSelect = async (event, pattern) => {
    setToggle(true);
    setPattern(pattern);
    await getWorld({ pattern, dispatch });
  };

  // Reset remnants of any previous game
  // Fetch services + patterns
  const cleanSlate = () => {
    updateInputMailbox('reset');
    Promise.all([dispatch(getServices()), dispatch(getPatterns())]);
  };

  useEffect(() => {  
    cleanSlate();
    // Listen for when patterns are updated
    proposalUpdated((data) => {
      setToggle(!!data.pattern_slug);

      if(data.pattern_slug) {
        setToggle(true);
        setProposal(data);
      } else {
        cleanSlate();
      }
    });
  
    // Listen for when train mailbox recieves updates
    trainMailboxUpdated((data) => {
      if(data.input) {
      
      }
    });
  }, [dispatch]);

  return (
    <div className="mainContainer">
      <div className="mainWrapper">
        {proposal && !proposal.pattern_slug && ( 
          <div className="mainContent">
            <h2>Choose your adventure</h2>
            <div className="row">
              {state.coreReducer.patterns?.map((p, index) => (
                <button
                  type="button"
                  key={index}
                  onClick={(event) => handlePatternSelect(event, p)}
                >
                  {`${p.name}`}
                </button>
              ))}
            </div>
          </div>
        )}
        {toggled && <Dashboard proposal={proposal} selectedPattern={pattern} isSimulator={simulator} />}
        {!toggled && (<a href="#" onClick={() => setAdminView(!adminView)}>Toggle admin view</a>)}
        {adminView && (
          <div>
            <h2>Admin View</h2>
            {!toggled && (
              <div className="row">
                <ToggleButton
                  label="(Admin) Switch on simulator: "
                  onChange={handleSimulator}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Main;
