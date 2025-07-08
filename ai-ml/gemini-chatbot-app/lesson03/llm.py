from google import genai
from google.genai.types import HttpOptions, GenerateContentConfig

# Gemini AI model name
# MODEL_NAME = "gemini-2.0-flash-lite-001"
MODEL_NAME = "gemini-2.5-flash-lite-preview-06-17"

# Gemini AI client
#  - Using environment variables to pass essential parameters to the client.
#  - Read more at https://github.com/googleapis/python-genai/tree/main?tab=readme-ov-file#create-a-client
client = genai.Client(http_options=HttpOptions(api_version="v1"))

# Create chat session
def get_chat_session():
    chat_session = client.chats.create(
        model=MODEL_NAME,
        config=GenerateContentConfig(
            system_instruction=[
                "You're a helpful Gemini AI Chatbot.",
                "Answer user's questions and use simple and clear language."
                "When possible, reply to user's question with a single sentence or a few sentences.",
                "Free to use emojis."
                "Be open and friendly. Don't be afraid to ask questions or clarify things.",
            ]
        ),
    )
    # Print chat session ID
    print(f"Chat session ID: {id(chat_session)}")
    return chat_session

if __name__ == "__main__":
    # Initialize chat session
    chat_session = get_chat_session()

    # CLI - Chat Session
    print("Enter your question (or 'exit' to quit)")
    while user_input := input("\nUser: "):
        if user_input.lower() == "exit":
            print("Exiting the chat session. Goodbye!")
            break
        # Send a message to LLM
        response = chat_session.send_message(user_input)
        print(f"Model: {response.text}")
