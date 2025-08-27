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

export async function POST(request: Request) {
  let result = "";
  const body = await request.json();
  const { prompt, model, url, maxTokens, temparature } = body;

  try {
    const response = await fetch(`${url}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: model,
        messages: [
          {
            role: "system",
            content:
              "you are an helpful ai assistant. you will answer the users questions. be brief and to the point. try to be factual and kind. do not use slang or jargon. do not use abbreviations. do not use emojis. try to keep your answers short and simple.",
          },
          {
            role: "user",
            content: prompt,
          },
        ],
        max_completion_tokens: maxTokens,
        temperature: temparature,
      }),
    });
    const json = await response.json();

    result = json.choices[0].message.content;

    return new Response(JSON.stringify({ message: result }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return new Response(JSON.stringify({ message: "Error" }), {
      status: 500,
      headers: { "Content-Type": "application/json" },
    });
  }
}
