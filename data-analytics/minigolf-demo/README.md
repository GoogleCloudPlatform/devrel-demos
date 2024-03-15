# Gemini Golf
This repository contains the code for the Gemini Golf demo, an interactive mini-golf experience that showcases a new approach to broadcasting the sport.

## Project Overview
Gemini Golf utilizes live data visualization and analysis to enhance the spectating experience. The system captures gameplay data through a GoPro camera and processes it using OpenCV and Python. This data drives two key features:

- AI-Powered Announcer: Gemini, a large language model, provides real-time commentary based on the player's performance, offering insights and observations in a professional sportscaster style.
- Personalized User Dashboard: A user-friendly dashboard visualizes key gameplay data, including shot heatmap and relevant statistics.

## Technical Details
- Data Capture: Gameplay is recorded using a GoPro camera and transferred wirelessly to a Pixel phone via the Quik app.
- Data Processing: The video is downloaded to the Pixel phone and uploaded to a cloud bucket by a Raspberry Pi. A cloud function analyzes the video frame-by-frame using OpenCV to detect the ball and hole locations, calculating distances.
- AI Announcer: The analysis data is used as input for Gemini, which generates real-time commentary based on the player's performance.
- User Dashboard: The analysis data is also used to populate a user-friendly dashboard with visualizations and statistics.

## Demo Execution
The demo is designed to be run at events and showcases. It requires a designated space with a single-hole minigolf course, a GoPro camera, a Pixel phone, a Raspberry Pi, and a display for the user dashboard.

## Getting Started
To run the demo, follow these steps:

1. Set up the hardware components as described in the PRD.
1. Clone this repository.
1. Install the required dependencies.
1. Configure the cloud function and storage bucket.
1. Run the Python script for data analysis.
1. Start the Gemini announcer and user dashboard applications.

## Technologies Used
- OpenCV: For object detection and trajectory tracking of the ball.
- Gemini Pro: For text-based real-time commentary generation.
- Cloud Functions: For serverless data processing and analysis.
- Raspberry Pi: For data transfer and cloud upload.

## License
This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.

