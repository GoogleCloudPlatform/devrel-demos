/**
 * Copyright 2025 Google LLC
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

"use client";
import type { model } from "@/app/types";

import { useEffect, useState } from "react";
import { Button } from "@heroui/button";
import { Slider } from "@heroui/slider";
import { Input } from "@heroui/input";

import { modelInfo } from "@/app/actions";
import { LLMOutput } from "@/components/llmoutput";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [output, setOutput] = useState("");
  const [temperature, setTemperature] = useState<number>(0.3);
  const [maxTokens, setMaxTokens] = useState<number>(128);
  const [models, setModels] = useState<model[]>([]);

  const handleModelLoad = async () => {
    const models = await modelInfo();

    setModels(models);
  };

  useEffect(() => {
    handleModelLoad();
  }, []);

  const handleOutput = () => {
    setOutput(prompt);
  };

  // ...existing code...
  const handleTemperatureChange = (value: number | number[]) => {
    if (typeof value === "number") {
      setTemperature(value);
    }
  };

  const handleMaxTokensChange = (value: number | number[]) => {
    if (typeof value === "number") {
      setMaxTokens(value);
    }
  };

  return (
    <main>
      <div className="grid grid-cols-12 gap-4 items-center justify-center">
        <Input
          className="col-span-10"
          label="Prompt"
          value={prompt}
          onValueChange={setPrompt}
        />
        <Button className="col-span-2" color="primary" onPress={handleOutput}>
          Generate
        </Button>
      </div>
      <div className="flex flex-row gap-4 py-4">
        <Slider
          label="Temparature"
          maxValue={1}
          minValue={0.0}
          step={0.1}
          value={temperature}
          onChange={handleTemperatureChange}
        />
        <Slider
          label="Max Tokens"
          maxValue={2048}
          minValue={1}
          step={1}
          value={maxTokens}
          onChange={handleMaxTokensChange}
        />
      </div>
      <div className="grid lg:grid-cols-12 grid-cols-4 gap-4">
        {models.map((model, index) => {
          return (
            <LLMOutput
              key={index}
              maxTokens={maxTokens}
              model={model}
              prompt={output}
              setPrompt={setPrompt}
              temperature={temperature}
            />
          );
        })}
      </div>
    </main>
  );
}
