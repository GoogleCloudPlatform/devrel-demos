# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import gradio as gr
import os

google_blue = gr.themes.colors.Color(
    name="google_blue",
    c50="#E8F0FE",
    c100="#D2E3FC",
    c200="#AECBFA",
    c300="#8AB4F8",
    c400="#669DF6",
    c500="#4285F4",
    c600="#1A73E8",
    c700="#1967D2",
    c800="#185ABC",
    c900="#174EA6",
    c950="#212B3C",
)
google_green = gr.themes.colors.Color(
    name="google_green",
    c50="#E6F4EA",
    c100="#CEEAD6",
    c200="#A8DAB5",
    c300="#81C995",
    c400="#5BB974",
    c500="#34A853",
    c600="#1E8E3E",
    c700="#188038",
    c800="#137333",
    c900="#0D652D",
    c950="#0D652D",
)

# blue theme
google_blue_theme = gr.themes.Default(
    primary_hue=google_green,
    secondary_hue="gray",
    neutral_hue=google_blue,
    text_size=gr.themes.sizes.text_lg,
)
google_blue_theme.body_background_fill_dark="#212B3C"

# blue theme
google_green_theme = gr.themes.Default(
    primary_hue=google_blue,
    secondary_hue="gray",
    neutral_hue=google_green,
    text_size=gr.themes.sizes.text_lg,
)
google_green_theme.body_background_fill_dark="#0D652D"

# Returns a theme using Google color palette based on THEME environment variable
def google_theme():
  # default to blue
  google_theme = "blue"
  if "THEME" in os.environ:
    google_theme = os.environ["THEME"]
  
  match google_theme:
    case "blue":
      return google_blue_theme
    case "green":
      return google_green_theme
    case __:
      return google_blue_theme