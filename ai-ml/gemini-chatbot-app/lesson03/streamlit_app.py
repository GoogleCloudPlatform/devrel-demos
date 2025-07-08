import streamlit as st
import llm
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

st.title("🤖 Chatbot with "
         "[⚡ Gemini-2.5-Flash-Lite](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite)"
         " & "
         "[🜲 Streamlit](https://streamlit.io/)")

st.markdown(
    "This is a Streamlit demo chatbot that uses Google's latest [Gemini-2.5-Flash-Lite 🔦](https://cloud.google.com/vertex-ai/generative-ai/docs/models/gemini/2-5-flash-lite). "
    "Read more about it [here](https://deepmind.google/technologies/gemini/flash/)."
)

# Initialize chat session in Streamlit's session state.
# This will be run only once, on the first run of the session.
if "chat_session" not in st.session_state:
    logging.info("New chat session initialized.")
    st.session_state.chat_session = llm.get_chat_session()

# Display chat history from the session state
for message in st.session_state.chat_session.get_history():
    with st.chat_message("assistant" if message.role == "model" else "user"):
        st.markdown(message.parts[0].text)


# Handle user input
if prompt := st.chat_input("What is up?"):
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    logging.info(f"User: {prompt}")

    # Get and display assistant response
    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            logging.info(f"Model: {response.text}")
        except Exception as e:
            logging.error(
                f"An error occurred while sending message to LLM: {e}", exc_info=True
            )
            st.error(f"An error occurred: {e}")
