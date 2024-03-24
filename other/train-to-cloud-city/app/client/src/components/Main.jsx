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
} from "../actions/coreActions";
import "./styles/Main.css";

/**
 * Main
 * -----------------
 *
 */
const Main = (props) => {
  const state = useSelector((state) => state);
  const dispatch = useDispatch();
  const [adminView, setAdminView] = useState(false);
  const [toggled, setToggle] = useState(false);
  const [simulator, setSimulator] = useState(false);

  useEffect(() => {
    async function fetchData() {
      await Promise.all([
        dispatch(getServices()),
        dispatch(getPatterns())
      ]);
    };
    fetchData();
  }, [dispatch]);

  // Turn on simulator
  const handleSimulator = async (event) => {
    setToggle(event.target.checked);
    setSimulator(event.target.checked);
    await getWorld({
      dispatch,
      isSimulator: event.target.checked,
    });
  };

  // Manually select pattern
  const handlePatternSelect = async (event, pattern) => {
    setToggle(true);
    await getWorld({ pattern, dispatch });
  };

  return (
    <div className="mainContainer">
      <div className="mainWrapper">
        { !toggled && <a href="#" onClick={()=> setAdminView(!adminView)}>Toggle admin view</a> }
        {!adminView && (
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
        {toggled &&<Dashboard isSimulator={simulator} />}
      </div>
    </div>
  );
};

export default Main;
