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

import React, { useState } from "react";
import "./styles/ToggleButton.css";

/**
 * ToggleButton
 * -----------------
 *
 */
const ToggleButton = (props) => {
  const { label, onChange } = props;
  const [toggled, setToggle] = useState(false);

  const handleChange = (event) => {
    setToggle(event.target.checked);
    onChange?.(event);
  };

  return (
    <div className="toggleContainer">
      {label}{" "}
      <div className="toggleWrapper">
        <input
          type="checkbox"
          className="checkbox"
          checked={toggled && "checked"}
          name={label}
          id={label}
          onChange={handleChange}
        />
        <label className="label" htmlFor={label}>
          <span className="inner" />
          <span className="switch" />
        </label>
      </div>
    </div>
  );
};

export default ToggleButton;
