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
import { required, composeValidators, validateServices } from "../helpers/formValidation";
import { Form, Field } from "react-final-form";
import { addCar, deleteCar } from "../actions/trainActions";
import {
  getServices,
} from "../actions/coreActions";
import ExtrasQRCode from "../assets/qrcode-extras.png";
import "./styles/QuizForm.css";

/**
 * QuizForm
 * -----------------
 *
 */
const QuizForm = (props) => {
  const { selectedPattern } = props;
  const state = useSelector((state) => state);
  const dispatch = useDispatch();

  const [errorMessage, setErrorMessage] = useState({ message: '', result: {} });
  const [successMessage, setSuccessMessage] = useState({ message: '', result: {} });

  useEffect(() => {
    async function fetchData() {
      await dispatch(getServices());
    };
    fetchData();
  }, [dispatch]);

  const services = state.coreReducer.services;

  const onSubmit = async (results) => {
    const proposal = {
      service_slugs: Object.keys(results).map((k) => results[k])
    };
   
    let result, error;

    try {
      // TODO: pass through current pattern/mission and proposal
      result = await validateServices(selectedPattern, proposal);
      setSuccessMessage(result);
      setErrorMessage(); // reset
      // TODO: pass through current pattern/mission and proposal
      //values.map((service) => dispatch(addCar(service)));
    } catch (error) {
      setSuccessMessage(); // reset
      setErrorMessage(error);
    }
  };

  const onReset = async (formReset) => {
    formReset();
    dispatch(deleteCar());
  };

  return selectedPattern?.checkpoints?.length === 0 ? (
    <div> No checkpoints available. </div>
  ) : (
    <Form
      onSubmit={onSubmit}
      render={({ handleSubmit, form, submitting, pristine, values }) => (
        <form id="missionForm" onSubmit={handleSubmit}>
          <p>Goal: {selectedPattern?.description}</p>
          {selectedPattern?.checkpoints?.map((step, index) => (
            <Field
              key={`missionStep${index}`}
              name={`missionStep${index}`}
              validate={composeValidators(required)}
            >
              {({ input, meta }) => (
                <div className="formMissionInputWrapper">
                  <div className="formMissionDescription">
                    {`Step ${index + 1}: ${step.description}`}
                  </div>
                  <div className="formMissionInput">
                    <label>Service: </label>
                    <select {...input} name="gcp" id="gcpService">
                      <option value="">--Choose a service--</option>
                      {services?.map((s, index) => (
                        <option key={index} value={`${s}`}>
                          {s}
                        </option>
                      ))}
                    </select>
                    {meta.error && meta.touched && (
                      <span className="formError">{meta.error}</span>
                    )}
                  </div>
                </div>
              )}
            </Field>
          ))}
          <div className="buttons">
            <button type="submit" disabled={submitting}>
              Submit
            </button>
            <button
              type="button"
              onClick={() => onReset(form.reset)}
              disabled={submitting || pristine}
            >
              Reset
            </button>
          </div>
          {(submitting || errorMessage?.message || successMessage?.message) && (
            <div className="resultContainer">
              {submitting && 'Calculating responses ....'}
              {errorMessage?.message && (
                <div>
                  <h3>{'Oh no!'}</h3>
                  <p>{errorMessage.message}</p>
                </div>
              )}
              {successMessage?.message && (
                <div>
                  <h3>{'Huzzah!'}</h3>
                  <p>{successMessage.message}</p>
                  <img alt="Extras" src={ExtrasQRCode} className="qrcode" />
                </div>
              )}
            </div>
          )}
        </form>
      )}
    />
  );
};

export default QuizForm;
