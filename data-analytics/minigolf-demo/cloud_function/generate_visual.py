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

import matplotlib.pyplot as plt
import numpy as np

CUSTOM_PALETTE = {
        1: "#4285F4", # Google Core scheme
        2: "#34A853",
        3: "#FBBC04",
        4: "#EA4335",
        5: "#63BDFD", # Google Highlight scheme
        6: "#18D363",
        7: "#FFE000",
        8: "#FF8080",
        9: "#4285F4", # Google Core scheme
        10: "#34A853",
        11: "#FBBC04",
        12: "#EA4335",
        13: "#63BDFD", # Google Highlight scheme
        14: "#18D363",
        15: "#FFE000",
        16: "#FF8080",
    }


def generate_visual(df, user_id):
    img = plt.imread(f"/tmp/BG_{user_id}.jpg")
    img = np.rot90(img, k=1, axes=(1,0))
    fig, ax = plt.subplots(figsize=(10.80, 19.20))
    plt.subplots_adjust(left=0, right=1, bottom=0, top=1)

    color_palette = [CUSTOM_PALETTE[shot_number] for shot_number in df['shot_number'].unique()]
    df['x'], df['y'] = 1080 - df['y'], df['x'] # For vertical visual

    shot_groups = df.groupby('shot_number')
    for i, (shot_number, data) in enumerate(shot_groups):
        ax.scatter(
            data['x'], 
            data['y'], 
            label=f"Shot {shot_number}", 
            color=color_palette[i], 
            s=15, 
            marker='o', 
            edgecolors='white', 
            linewidths=0.25
        )
    ax.legend()

    # plt.gca().invert_yaxis()
    # plt.gca().invert_xaxis()

    # Remove axis labels and ticks
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')

    ax.imshow(img)
    plt.savefig('/tmp/trajectory.png')
    return
