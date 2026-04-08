# Sample code for Google Cloud Next '26 Codelab

This directory contains the sample code and resources used for the **"Build an AI-powered customer support agent using Firebase AI Logic"** codelab at Google Cloud Next '26.

## Overview

The demo guides users through building a sophisticated AI-powered customer support agent for "Rugged Outdoor Store" using **Firebase AI Logic**. This application demonstrates how to use server-managed prompt templates to enforce complex business logic (like "Appeasement Budgets") and interact with product catalogs securely and efficiently.

## Directory structure

The files are organized into source code, configuration, and prompt templates:

*   **`src/`**: Contains the **React and TypeScript source code** for the customer support dashboard and chat interface.
*   **`product-agent.prompt`**: Defines the **Firebase AI Logic prompt template**, including system instructions, role definitions, and business rules for the AI agent.
*   **`src/data/`**: Includes sample **product catalog data** (`products.json` and `products.txt`) used to ground the AI agent's responses.
*   **`firebase.json`**: Standard **Firebase configuration** file for project settings and deployment.

## How to use these files

To replicate the demo, follow the steps outlined in the [Build an AI-powered customer support agent using Firebase AI Logic Codelab](https://codelabs.developers.google.com/next26/firebase-ai-logic-support-agent).

1.  **Clone this repository** to your local machine or Cloud Shell.
2.  **Install dependencies**:
    *   Navigate to this directory and run `npm install`.
3.  **Configure Firebase**:
    *   Initialize a Firebase project and enable the **Vertex AI for Firebase** extensions.
    *   Update `src/firebase.ts` with your web app's configuration.
4.  **Run the application**:
    *   Start the development server with `npm run dev`.
    *   Interact with the "Rugged Operator" AI agent through the web interface.
