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

import { getAI, getTemplateGenerativeModel, AgentPlatformBackend } from "firebase/ai";
import { initializeAppCheck, ReCaptchaV3Provider } from "firebase/app-check";
import { initializeApp } from "firebase/app";

// Your web app's Firebase configuration
const firebaseConfig = {
    // paste your Firebase config here
};

// Initialize Firebase
export const app = initializeApp(firebaseConfig);

// Initialize App Check
initializeAppCheck(app, {
  provider: new ReCaptchaV3Provider('YOUR_RECAPTCHA_SITE_KEY'),
  isTokenAutoRefreshEnabled: true
});

const ai = getAI(app, { backend: new AgentPlatformBackend(), useLimitedUseAppCheckTokens: true });

const model = getTemplateGenerativeModel(ai);
export const callCustomerSupportModel = async (query: string, productId?: string, history?: { role: string, contents: string }[]) => {
    // Generate content using the published 'product-agent' template
    const result = await model.generateContent('product-agent', {
        query,
        productId,
        history,
    });
    return result.response.text();
}
