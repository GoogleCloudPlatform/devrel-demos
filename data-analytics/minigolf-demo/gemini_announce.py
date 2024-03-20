# Copyright 2024 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     https://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import vertexai
from vertexai.preview.generative_models import GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

VIDEO = Part.from_uri(uri="gs://test_golf/GX010055.MP4", mime_type="video/mp4")

if __name__ == "__main__":
    vertexai.init(project="next-2024-golf-demo-01", location="us-central1")
    model = GenerativeModel("gemini-1.5-pro-preview-0215")
    responses = model.generate_content(
        [
           VIDEO, 
           """ how many shots the player made in this video?
           is the ball in the hole at the end?
           """
        ],
        generation_config={
            "max_output_tokens": 8192,
            "temperature": 2,
            "top_p": 0.4
        },
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
        },
        stream=False,
    )
    print(responses.text)

"""
           You are a professional golf announcer and you must broadcast the match an enthusiastic tone. You should use the following context.
           - The match is \"Google Cloud Next - Minigolf Championship final\", and the venue is in Las Vegas.
           - The competitor already completed the game and if the player complete this hole within three shots, the player wins.
           - If the hole is completed over four shots, the competitor wins.
           - You should not mention anything, including the player\'s appearance, as it is against PII.
           - The broadcast must be done in colloquial language and no additional text other than the announcer\'s comments (e.g., cheers from the audience) must be included).
           - Make sure you should provide only the broadcast script.
           
           - The course is a rectangle measuring 7 feet by 20 feet, and there are no obstacles or slopes on the course.
           - Describe each shots in detail.
         """