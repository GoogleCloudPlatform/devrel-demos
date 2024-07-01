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
from vertexai.generative_models import GenerativeModel, Image, Part
import vertexai.preview.generative_models as generative_models

TITLE = "Google Marketing Live - Minigolf Championship final"
VENUE = "Grand Intercontinental Seoul Parnas Grand Ballroom"
LANGUAGE = "Korean"
GEMINI_MODEL = "gemini-1.5-pro-001"

SYSTEM_INSTRUCTION = f"""
You are a team of two professional golf broadcasters covering the final hole of the {TITLE} at the {VENUE}. Use {LANGUAGE} to display result.
Each Announcer and Commentator's line must start on a new line. Once the announcer's or the commentator's dialogue has ended, use line breaks to clearly separate.
You will receive precise shot information for the final hole. This information is extracted from video analysis and is 100% accurate. You MUST base your commentary strictly on this data, especially the number of shots taken and the outcome of each shot.
**IMPORTANT - Never say "Hole in one" if the number of shot is greater than one.
Also use provided raw video and a photo. The photo shows the player's ball trajectory and shot sequence.
- Use markdown syntax appropriately.
- Refer to the player as "player" or "they".
- Avoid commentary on the player's appearance.
- Focus on the commentary; do not include sound effects.

Background:
- The competitor has already finished their round and is currently ahead.
- The player needs to finish this hole at par or better (three shots or less) to win the championship.
- If they score a bogey or worse (four shots or more), the competitor will win.
- Don't reveal the exact score difference, just emphasize that the player needs a good performance on this final hole to secure victory.

Announcer (Play-by-Play):
- Your role is to create excitement and capture the energy of the moment.
- Focus on describing the action as it unfolds, using vivid language and a dynamic tone.
- Don't just state what happened, describe the shot's trajectory in detail.
- Highlight the stakes of the final hole and React to the player's shots with enthusiasm.
- **Engage with the commentator, asking questions and prompting further analysis.**
- Paint a picture for the viewers so they feel like they are right there on the green.

Commentator (Analyst):
- Your role is to provide expert insights and analysis.
- Discuss the player's strategy: "Interesting choice to play it safe on this shot. They must be feeling the pressure."
- Evaluate the quality of the shots: "That was a textbook putt, perfectly executed. They read the green like a pro."
- Offer extended context about the tournament, the player's history, and the significance of this final hole.
- Share relevant statistics or historical data: "No player has ever won this tournament with a hole-in-one on the final hole. Could we witness history in the making?"
- Don't just provide facts, weave them into a compelling narrative.
- **Respond to the announcer's questions and comments with detailed explanations.**

**IMPORTANT - Prioritize the image provided**
"""
GENERATION_CONFIG = {
    "max_output_tokens": 8192,
    "temperature": 0,
    "top_p": 1,
}
SAFETY_SETTINGS = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}

def helper_shot_information(df):
    SHOT_DICT = {
        1: "Hole-in-one!",
        2: "birdie!",
        3: "par!",
        4: "bogey.",
        5: "double bogey.",
        6: "triple bogey.",
        7: "quadruple bogey.",
        8: "double par."
    }
    SHOT_NUM_DICT = {1: "1st", 2: "2nd", 3: "3rd"}
    filtered_df = df[df['shot_number'] > 0].sort_values(by='frame_number')
    is_last_shot_hole_in = filtered_df['distance'].iloc[-1] < 30
    total_shot_num = filtered_df['shot_number'].iloc[-1]
    grade = SHOT_DICT[total_shot_num] if total_shot_num <= 8 else SHOT_DICT[8]

    shot_details = []
    for i in range(1, total_shot_num + 1):
        shot = SHOT_NUM_DICT.get(i, f"{i}th")
        shot_details.append(f"The {shot} shot was ")
        if i < total_shot_num or (i == total_shot_num and not is_last_shot_hole_in):
            shot_details.append("not ")
        shot_details.append("hole-in.\n")
    shot_details = ''.join(shot_details)

    result = "didn't make" if is_last_shot_hole_in else "made"
    
    if is_last_shot_hole_in:
        result = f"made with {total_shot_num} shot/shots! {grade}"
        if total_shot_num > 3:
            result += " The player loses."
        else:
            result += " The player wins!"

    commentary = f"""
    {shot_details}
    The ball {result}
    """
    return commentary


def generate_commentary(project_id, bucket_name, user_id, df):
    vertexai.init(project=project_id, location="asia-northeast3")
    model = GenerativeModel(
        GEMINI_MODEL,
        system_instruction=SYSTEM_INSTRUCTION,
    )
    VIDEO = Part.from_uri(uri=f"gs://{bucket_name}/{user_id}.mp4", mime_type="video/mp4")
    IMAGE = Part.from_image(Image.load_from_file("/tmp/trajectory.png"))

    responses = model.generate_content(
        [VIDEO, IMAGE, helper_shot_information(df)],
        generation_config=GENERATION_CONFIG,
        safety_settings=SAFETY_SETTINGS,
    )
    return responses.text

# def query_data_to_dataframe(project_id, user_id):
#     from google.cloud import bigquery
#     bq_client = bigquery.Client()

#     BIGQUERY = f"{project_id}.minigolf_a.tracking"
#     query = f'SELECT * FROM {BIGQUERY} WHERE user_id = "{user_id}" AND shot_number > 0'
#     df = bq_client.query(query).to_dataframe()
#     return df

# if __name__ == "__main__":
#     df = query_data_to_dataframe("gml-seoul-2024-demo-01", "minigolf_0015")
#     res = generate_commentary("gml-seoul-2024-demo-01", "video_gml_test_a", "minigolf_0015", df)
#     print(res)