#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Generate Heatmap Visualizations for Inspect AI Evaluations.

This script demonstrates how to extract evaluation data using the Inspect AI
analysis API and render it as a heatmap using the inspect_viz package.
This corresponds to Lesson 2 of the blog tutorial.
"""

import argparse
import os
import sys
from inspect_ai.analysis import evals_df, model_info, prepare
from inspect_viz import Data
from inspect_viz.view import scores_heatmap
from inspect_viz.plot import legend, write_html


def generate_heatmap(log_dir: str, output_file: str | None = None, height: int = 420, width: int = 800):
    """
    Reads Inspect AI logs from log_dir and generates a score heatmap.
    """
    if not os.path.isdir(log_dir):
        print(f"Error: Log directory '{log_dir}' does not exist.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading logs from: {log_dir}")
    
    # 1. Extract Dataframe using Inspect AI's analysis tools
    df = evals_df(log_dir)

    if df.empty:
        print(f"Warning: No evaluation logs found in '{log_dir}'.", file=sys.stderr)
        return None

    print(f"Found {len(df)} evaluation records.")

    # 2. Prepare Data (Add display names)
    # This ensures 'model_display_name' is available for the heatmap
    df = prepare(df, [model_info()])

    # 3. Wrap Dataframe in Inspect Viz Data container
    viz_data = Data.from_dataframe(df)

    # 4. Render Heatmap with Top-Anchored Legend
    margin_left = 200
    margin_right = 20
    margin_top = 50
    legend_top_offset = 30                                 # Extra canvas height allocated for top legend margin
    grid_center_shift = -(margin_left - margin_right) / 2  # Center legend on visible heatmap grid

    top_legend = legend(
        "color",
        frame_anchor="top",
        width=width / 2,            # Exact original legend width (400px)
        inset_x=grid_center_shift,  # Center legend horizontally on visible heatmap grid
        border=False,
        background=False
    )

    print("Rendering heatmap with top-anchored legend...")
    plot = scores_heatmap(
        viz_data,
        height=height + legend_top_offset,
        width=width,
        margin_left=margin_left,  # Prevent long model names from truncation
        margin_top=margin_top,    # Top margin to place legend above heatmap grid
        margin_bottom=110,        # Accommodate 45-degree rotated X-axis tick labels
        orientation="horizontal",
        sort={"x": "x"},          # Sort skills alphabetically while resolving column fallbacks
        legend=top_legend         # Anchor legend at top of plot
    )

    # 5. Handle Output
    if output_file:
        write_html(output_file, plot)
        print(f"Heatmap saved to: {output_file}")
        print(f"You can open this file in your browser to view the interactive heatmap.")

    return plot


def main():
    parser = argparse.ArgumentParser(description="Generate score heatmaps from Inspect AI logs using inspect_viz.")
    parser.add_argument("log_dir", nargs="?", default="logs", help="Directory containing Inspect AI evaluation logs (.eval files). Defaults to 'logs'.")
    parser.add_argument("-o", "--output", help="Output file for the heatmap (e.g., 'heatmap.html'). Optional.")
    parser.add_argument("--height", type=int, default=420, help="Height of the plot in pixels. Defaults to 420.")
    parser.add_argument("--width", type=int, default=800, help="Width of the plot in pixels. Defaults to 800.")

    args = parser.parse_args()

    # If output is specified, try to generate it
    generate_heatmap(
        log_dir=args.log_dir,
        output_file=args.output,
        height=args.height,
        width=args.width
    )
    
    print("\n💡 Tip: To view this heatmap interactively, run this script in a Jupyter Notebook or Quarto document without the -o flag.")



if __name__ == "__main__":
    main()
