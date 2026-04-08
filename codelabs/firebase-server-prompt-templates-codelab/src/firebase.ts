/**
 * Copyright 2026 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import { getAI, getTemplateGenerativeModel, VertexAIBackend } from "firebase/ai";
import { initializeApp } from "firebase/app";

// Your web app's Firebase configuration
const firebaseConfig = {
    // paste your Firebase config here
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);

const ai = getAI(app, { backend: new VertexAIBackend() });

const model = getTemplateGenerativeModel(ai);

export const callCustomerSupportModel = async (query: string, productId?: string, history?: { role: string, contents: string }[]) => {
    const result = await model.generateContent('product-agent', {
        query,
        productId,
        history,
    });
    return result.response.text();
}
