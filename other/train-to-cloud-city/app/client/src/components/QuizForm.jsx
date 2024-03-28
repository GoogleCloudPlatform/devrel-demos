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
import {
  required,
  composeValidators,
  validateServices,
} from "../helpers/formValidation";
import { Form, Field } from "react-final-form";
import { updateCargo, getServices } from "../actions/coreActions";
import ExtrasQRCode from "../assets/qrcode-extras.png";
import "./styles/QuizForm.css";

/**
 * QuizForm
 * -----------------
 *
 */
const QuizForm = (props) => {
  const { selectedPattern, proposalResult } = props;
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  const [errorMessage, setErrorMessage] = useState({ message: "", result: {} });
  const [successMessage, setSuccessMessage] = useState({
    message: "",
    result: {},
  });

  useEffect(() => {
    dispatch(getServices());
  }, [dispatch]);

  const services = state.coreReducer.services;

  const onSubmit = async (results) => {
    const slugs = Object.keys(results).map((k) => results[k]);
    try {
      dispatch(updateCargo(slugs));
      setSuccessMessage("Submitted");
      setErrorMessage(); // reset
    } catch (error) {
      setSuccessMessage(); // reset
      setErrorMessage(error);
    }
  };

  return selectedPattern?.checkpoints?.length === 0 ? (
    <div> No checkpoints available. </div>
  ) : (
    <Form
      onSubmit={onSubmit}
      render={({ handleSubmit, form, submitting, pristine, values }) => (
        <form id="missionForm" onSubmit={handleSubmit}>
          <p>
            <b>Goal: </b>
            {selectedPattern?.description}
          </p>
          {selectedPattern?.checkpoints?.map((step, index) => (
            <p>
              <b>{`Step ${index + 1}: `}</b>
              {step.description}
            </p>
          ))}
          <div className="resultContainer">
            {!proposalResult?.clear && (
              <div>
                <h3>{"Oh no!"}</h3>
                <p>{errorMessage.message}</p>
              </div>
            )}
            {proposalResult?.clear && (
              <div>
                <h3>{"Huzzah!"}</h3>
                <p>{proposalResult?.reason}</p>
                <img alt="Extras" src={ExtrasQRCode} className="qrcode" />
              </div>
            )}
          </div>
        </form>
      )}
    />
  );
};

export default QuizForm;
