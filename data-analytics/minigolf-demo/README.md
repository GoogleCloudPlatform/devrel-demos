# Golf with Gemini
This repository contains the code for the `Golf with Gemini` demo, an interactive mini-golf experience that showcases cutting-edge technology to transform the way we engage with the sport.

## Project Overview
`Golf with Gemini` combines live data visualization and analysis to create an insightful and engaging experience. The system captures gameplay data using a camera and processes it with OpenCV. This data drives three key features:

- AI-Powered Announcer: Gemini, a large language model, provides real-time commentary based on the player's performance, offering insights and engaging commentary in the style of a professional sportscaster.
- Personalized User Dashboard: A dashboard visualizes key gameplay data, including statistics and plots of each shot, providing players with valuable insights into their performance.
- Real-time Analytics and Streaming Upload to BigQuery: Gameplay data is streamed directly to BigQuery, enabling real-time analysis and visualization of player performance. This allows for immediate feedback and insights, enhancing the overall experience.

The key aspect of this demo is how Gemini combines video and text information. It doesn't just analyze the video or generate text independently; it uses the video data to inform and enrich the generated commentary, making it more relevant and insightful. This demonstrates the power of multimodal AI, where different modalities complement each other to create a richer and more comprehensive understanding of the situation.

## Technical Details
- Data Capture: Gameplay is recorded using a camera and transferred to the Cloud Storage bucket.
- Data Processing: Once a cloud bucket contains the video, a Cloud Function analyzes the video frame-by-frame using OpenCV to detect the ball and hole locations, calculating distances and other metrics, like number of shots.
    - Real-time Streaming: Simultaneously, the data is streamed directly to BigQuery for real-time analysis and visualization.
- AI Announcer: The analyzed data is fed into Gemini, which generates real-time commentary based on the player's performance.
- User Dashboard: The analyzed data is also used to populate a user-friendly dashboard with visualizations and statistics, providing insights derived from both real-time and historical data.

## File Structure
Here's a breakdown of each file in the repository and how they contribute to the `Golf with Gemini` demo:

### helper.py: 
This script handles various helper functions for the demo, including:

- Defining ROI(Regions Of Interest): It allows you to specify the areas in the video frame where the golf ball and hole are located.
- Video processing: It uses OpenCV to track the ball's movement in the video, calculating distances and other metrics.

### upload.py: 
This script continuously monitors a designated directory for new video files. When a new video is detected, it automatically uploads it to the designated Cloud Storage bucket, triggering the image_recognition Cloud Function to process the video.

### image_recognition.py: 
This script is deployed as a Cloud Function and is triggered whenever a new video is uploaded to Cloud Storage. It performs the following tasks:

- Video processing: Similar to helper.py, it uses OpenCV to track the ball's movement and detect shots.
- Data storage: It stores the extracted tracking data (ball position, distance, shot number, etc.) in BigQuery for further analysis and visualization.

### bq_notebook.ipynb: 
This Jupyter Notebook is responsible for data analysis and visualization. It connects to BigQuery to retrieve the processed data and generates insights such as:

- Overall player statistics: It calculates and displays metrics like the average and median number of shots taken by all players.
- Individual player journey visualization: It creates a scatter plot showing the trajectory of the ball for a specific player, allowing them to visualize their performance.
- AI-powered commentary generation: It leverages Gemini to generate real-time commentary based on the player's performance data.

## Initial Setup
### Hardware:
- Webcam: Mounted above the hole, capturing the tee and hole, and connected to the laptop.
- Chromebook (x1): Connects to the webcam to control recording and uploading a video.

### Software:
- OpenCV: For object detection and ball tracking.
- Gemini Pro: For generating real-time commentary.
- Cloud Functions: For serverless data processing and analysis.

## Demo Execution
The demo is designed for events and showcases, requiring a dedicated space with a single-hole minigolf course, a camera supports 1080p/60fps, a laptop (preferrably Chromebook), and a display for the user dashboard.

## License
This project is licensed under the Apache License, Version 2.0. See the LICENSE file for details.
