/*
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     https://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.google.EventGen;

public enum KafkaScenario {
    DEFAULT("0"),
    LARGE_ANALYTICAL_DATA("1");

    private final String scenarioId;

    KafkaScenario(String scenarioId) {
        this.scenarioId = scenarioId;
    }

    public String getScenarioId() {
        return scenarioId;
    }

    public static KafkaScenario fromString(String text) {
        if (text != null) {
            for (KafkaScenario b : KafkaScenario.values()) {
                if (text.equalsIgnoreCase(b.scenarioId) || text.equalsIgnoreCase(b.name())) {
                    return b;
                }
            }
        }
        // Default to DEFAULT
        return DEFAULT;
    }
}
