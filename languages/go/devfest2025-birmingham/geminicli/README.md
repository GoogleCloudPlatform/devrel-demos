# Gemini CLI Demo

This project serves as a demonstration of the Gemini CLI's capabilities, showcasing its ability to:

- **Code Generation:** Develop both backend API services and frontend user interfaces.
- **Multi-modal Understanding:** Utilize an image as a reference for designing and implementing the frontend UI.

## Project Overview

The application consists of a simple FastAPI backend that provides a `/greetings` endpoint. This endpoint returns a personalized greeting if a `name` parameter is provided, or a default "hello world" message otherwise.

The frontend is a basic HTML, CSS, and JavaScript application that interacts with the backend. It allows users to input a name and retrieve a greeting, with its design inspired by a provided image reference.

## How to Run

This project is designed to be built and run using the Gemini CLI. Follow these steps:

1.  **Start the Gemini CLI.**
2.  **Run the Backend Prompt:**
    Provide the `PROMPT_BACKEND.md` file to the Gemini CLI to create the API server.
3.  **Test the Backend Server:**
    Once the server is running (you will be instructed to run `uv run uvicorn main:app`), you can test it by accessing the following URLs in your browser or with a tool like `curl`:
    -   `http://localhost:8000/greetings`
    -   `http://localhost:8000/greetings?name=foo`
4.  **Run the Frontend Prompt:**
    Provide the `PROMPT_FRONTEND.md` file to the Gemini CLI. Please make sure to check `image.png` as instructed in the prompt, as it serves as the design reference for the UI.
5.  **Access the UI:**
    After the frontend is set up and the server is running, open your web browser and navigate to `http://127.0.0.1:8000` to interact with the application.
