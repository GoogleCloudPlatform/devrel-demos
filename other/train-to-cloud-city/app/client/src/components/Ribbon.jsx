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
import "./styles/Ribbon.css";

/**
 * Ribbon
 * -----------------
 *
 */
const Ribbon = () => {
  return (
    <div className="ribbonContainer">
      <div className="ribbon">
        <div className="blue"></div>
        <div className="red"></div>
        <div className="yellow"></div>
        <div className="green"></div>
      </div>
    </div>
  );
};

export default Ribbon;

