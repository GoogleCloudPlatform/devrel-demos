import streamlit as st
from google import genai
from google.genai import types
import requests
import logging
import google.cloud.logging

# --- Logging  ---
logging.basicConfig(level=logging.INFO)
cloud_logging_client = google.cloud.logging.Client()
cloud_logging_client.setup_logging()

# --- Defining variables and parameters  ---
REGION = "global"
PROJECT_NAME = None  # TO DO: INSERT PROJECT NAME
GEMINI_MODEL_NAME = "gemini-2.5-pro-preview-06-05"

temperature = .2 # Controls the randomness of the model's output. A lower value makes it more deterministic.
top_p = 0.95 # Controls the diversity of the model's output.

# System instructions give the model its persona, rules, and goals.
system_instructions = """
You are a sophisticated travel assistant chatbot designed to provide comprehensive support to users throughout their travel journey. Your capabilities include answering travel-related questions, assisting with booking travel arrangements, offering detailed information about destinations, and providing support for existing travel plans.

**Core Functionalities:**

1.  **Travel Information and Recommendations:**
    *   Answer user inquiries about travel destinations, including popular attractions, local customs, visa requirements, weather conditions, and safety advice.
    *   Provide personalized recommendations for destinations, activities, and accommodations based on user preferences, interests, and budget.
    *   Offer insights into the best times to visit specific locations, considering factors like weather, crowds, and pricing.
    *   Suggest alternative destinations or activities if the user's initial choices are unavailable or unsuitable.

2.  **Booking Assistance:**
    *   Facilitate the booking of flights, hotels, rental cars, tours, and activities.
    *   Search for available options based on user-specified criteria such as dates, destinations, budget, and preferences.
    *   Present clear and concise information about available options, including pricing, amenities, and booking terms.
    *   Guide users through the booking process, ensuring accurate information and secure transactions.
    *   Provide booking confirmations and relevant details, such as booking references and contact information.

3.  **Travel Planning and Itinerary Management:**
    *   Assist users in creating detailed travel itineraries, including flights, accommodations, activities, and transportation.
    *   Offer suggestions for optimizing travel plans, such as minimizing travel time or maximizing sightseeing opportunities.
    *   Provide tools for managing and modifying existing itineraries, including adding or removing activities, changing booking dates, or upgrading accommodations.
    *   Offer reminders and notifications for upcoming travel events, such as flight check-in or tour departure times.

4.  **Customer Support and Troubleshooting:**
    *   Provide prompt and helpful support to users with questions or issues related to their travel plans.
    *   Assist with resolving booking discrepancies, cancellations, or modifications.
    *   Offer guidance on travel-related emergencies, such as lost luggage or travel delays.
    *   Provide access to relevant contact information for airlines, hotels, and other travel providers.

**Interaction Guidelines:**

*   **Professionalism:** Maintain a polite, respectful, and professional tone in all interactions.
*   **Clarity and Conciseness:** Provide clear, concise, and easy-to-understand information. Avoid jargon or technical terms unless necessary and always explain them.
*   **Accuracy:** Ensure all information provided is accurate and up-to-date. Double-check details before sharing them with users. If unsure about something, admit that you don't know and offer to find the information.
*   **Personalization:** Tailor your responses and recommendations to the specific needs and preferences of each user.
*   **Proactive Assistance:** Anticipate user needs and offer relevant information or suggestions proactively.
*   **Error Handling:** Gracefully handle user errors or misunderstandings. Provide helpful guidance and alternative options when necessary.
*   **Confidentiality:** Respect user privacy and handle personal information with the utmost confidentiality and in compliance with data protection regulations.

**Example Interactions:**

**User:** "I want to go on a beach vacation in the Caribbean. I have a budget of $2000 per person for a week."
**Chatbot:** "Certainly! The Caribbean offers many beautiful beach destinations within your budget. Some popular options include Punta Cana in the Dominican Republic, Cancun in Mexico, and Montego Bay in Jamaica. These destinations offer stunning beaches, all-inclusive resorts, and various activities. Would you like me to search for flights and accommodations for these locations based on your travel dates?"

**User:** "My flight is delayed. What should I do?"
**Chatbot:** "I'm sorry to hear about the delay. Please check with the airline for the updated departure time and any assistance they can offer. You may be entitled to compensation or rebooking options depending on the length of the delay and the airline's policy. Do you have your flight number handy so I can look up the current status for you?"

**User:** "Tell me about the best time to visit Japan."
**Chatbot:** "Japan is a fantastic destination with distinct seasons offering unique experiences. Spring (March-May) is famous for the beautiful cherry blossoms, while autumn (September-November) boasts stunning fall foliage. Both seasons have pleasant temperatures, making them ideal for sightseeing. Summer (June-August) can be hot and humid, but it's a great time for festivals and outdoor activities in the mountains. Winter (December-February) offers opportunities for skiing and snowboarding in the Japanese Alps, though some areas may experience heavy snowfall. To recommend the best time for you, could you tell me what you'd like to experience in Japan?"

By following these instructions, you will be able to provide exceptional travel assistance and create a positive experience for every user.
"""

# --- Tooling ---
weather_function = {
    "name": "get_current_temperature",
    "description": "Gets the current temperature for a given location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name, e.g. San Francisco",
            },
        },
        "required": ["location"],
    },
}

def get_current_temperature(location: str) -> str:
    """Gets the current temperature for a given location."""

    try:
        # --- Get Latitude and Longitude for the location ---
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        geocode_response = requests.get(geocode_url)
        geocode_data = geocode_response.json()

        if not geocode_data.get("results"):
            return f"Could not find coordinates for {location}."

        lat = geocode_data["results"][0]["latitude"]
        lon = geocode_data["results"][0]["longitude"]

        # --- Get Weather for the coordinates ---
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        weather_response = requests.get(weather_url)
        weather_data = weather_response.json()

        temperature = weather_data["current_weather"]["temperature"]
        unit = "°C"

        return f"{temperature}{unit}"

    except Exception as e:
        return f"Error fetching weather: {e}"

# --- Initialize the Vertex AI Client ---
try:
    # This client object is the main entry point for interacting with the Vertex AI SDK.
    client = genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=REGION,
    ) 

    print(f"VertexAI Client initialized successfully with model {GEMINI_MODEL_NAME}")

except Exception as e:
    st.error(f"Error initializing VertexAI client: {e}")
    st.stop()

def get_chat(model_name: str):
    """# This function manages the chat session. 
    It uses st.session_state to preserve the chat history and configuration 
    between user interactions in the Streamlit app."""
    if f"chat-{model_name}" not in st.session_state:
    # Initialize a new chat session if one doesn't exist for this model.

        # Define the tools configuration for the model
        tools = types.Tool(function_declarations=[weather_function])
        
        # Define the generate_content configuration, including tools
        generate_content_config = types.GenerateContentConfig(
            temperature=temperature,
            top_p=top_p,
            system_instruction=[types.Part.from_text(text=system_instructions)],
            tools=[tools] # Pass the tool definition here
        )

        # Create a new chat session with the specified configuration.
        chat = client.chats.create(
            model=model_name,
            config=generate_content_config,
        )

        # Store the new chat session in the Streamlit session state.
        st.session_state[f"chat-{model_name}"] = chat
        
    return st.session_state[f"chat-{model_name}"]

# --- Call the Model ---
def call_model(prompt: str, model_name: str) -> str:
    """
    This function interacts with a large language model (LLM) to generate text based on a given prompt.
    It maintains a chat session and handles function calls from the model to external tools.
    """
    try:
        chat = get_chat(model_name) # Get the existing chat session or create a new one.

        message_content = prompt # The initial message is the user's prompt.

        # Start the tool-calling loop
        while True:
            # Send the user's prompt or the tool's response to the model.
            response = chat.send_message(message_content)

            # Check if the model wants to call a tool
            has_tool_calls = False

            # Check the model's response for a function call.
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_tool_calls = True
                    function_call = part.function_call
                    logging.info(f"Function to call: {function_call.name}")
                    logging.info(f"Arguments: {function_call.args}")

                    # Call the appropriate function if the model requests it.
                    if function_call.name == "get_current_temperature":
                      result = get_current_temperature(**function_call.args)

                    # Prepare the tool's output to be sent back to the model.
                    function_response_part = types.Part.from_function_response(
                        name=function_call.name,
                        response={"result": result},
                    )

                    # The new message_content is now the output from our tool.
                    message_content = [function_response_part]
            # If no tool call was made, break the loop
            if not has_tool_calls:
                break

        # Return the model's final text response.
        return response.text
    except Exception as e:
        return f"Error: {e}"


# --- Presentation Tier (Streamlit) ---
# Set the title of the Streamlit application
st.title("Travel Chat Bot")

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    # Initialize the chat history with a welcome message
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you today?"}
    ]

# Display the chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Get user input
if prompt := st.chat_input():
    # Add the user's message to the chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display the user's message
    st.chat_message("user").write(prompt)

    # Show a spinner while waiting for the model's response
    with st.spinner("Thinking..."):
        # Get the model's response using the call_model function
        model_response = call_model(prompt, GEMINI_MODEL_NAME)
        # Add the model's response to the chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": model_response}
        )
        # Display the model's response
        st.chat_message("assistant").write(model_response)