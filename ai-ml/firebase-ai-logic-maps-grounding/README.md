# AI Travel Concierge - Firebase AI & Maps Grounding

This project demonstrates how to use the Firebase AI SDK with Google Maps Grounding to build a smart travel assistant. It allows users to enter a starting city and trip details, and generates a day-by-day itinerary with locations plotted on an interactive Google Map.

## What is this?

The `index.html` file is a self-contained web application that showcases the integration of:
- **Firebase AI SDK**: To communicate with Gemini models.
- **Google Maps Grounding**: To ensure the AI's recommendations are real, existing places verified by Google Maps.
- **Google Maps JavaScript API**: To display the locations on a map with interactive markers.

It provides a simple UI to input your API keys, project details, and travel preferences, and then renders a markdown-formatted itinerary along with a map showing the suggested spots.

## Prerequisites

To use this application, you will need:

1.  **A Google Cloud Project** with the following APIs enabled:
    -   **Maps JavaScript API**
    -   **Places API (New)**
    -   **Geocoding API**
2.  **An API Key** from your Google Cloud project that has permission to use the above Maps APIs and also the **Generative Language API** (for Gemini).
3.  **A Firebase Project** (the app uses Firebase initialization).
4.  **Firebase Project ID** and **App ID**.

## How to Run Locally

Since the application uses ES Modules and fetches resources, opening the file directly in your browser (`file://` protocol) may cause issues. It is recommended to serve it using a local HTTP server.

Here are a few ways to do that:

### Option 1: Using Node.js (npx)

If you have Node.js installed, you can use `npx` to start a quick server without installing anything globally:

```bash
# Using 'serve'
npx serve

# Or using 'live-server'
npx live-server
```

### Option 2: Using Python

If you have Python installed, you can use its built-in server:

```bash
# For Python 3.x
python -m http.server 8000
```

Then open your browser and navigate to `http://localhost:8000`.

## Usage

1.  Open the app in your browser using one of the methods above.
2.  Fill in the form fields:
    -   **API Key**: Your Google AI / Maps API key.
    -   **Firebase Project ID**: Your Firebase project ID.
    -   **Firebase App ID**: Your Firebase Web App ID.
    -   **Starting City**: The city where your trip begins.
    -   **Trip Details**: What you want to do (e.g., "3-day food tour").
3.  Click **Generate Itinerary**.
