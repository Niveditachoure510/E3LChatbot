import streamlit as st
import json
import os
import uuid
import random
import openai
from datetime import datetime

# Manually define ChatMessage class
class ChatMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content

# Constants
HISTORY_FILE = "conversation_history.json"
OPENAI_API_KEY = "your_openai_api_key"  # Replace with your actual OpenAI API key
MODEL_NAME = "gpt-3.5-turbo"  # Adjust model name if needed

# Load conversation history
def load_conversation_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as file:
                return json.load(file)
        except:
            return {"conversations": []}
    return {"conversations": []}

# Save conversation history
def save_conversation_history(history):
    with open(HISTORY_FILE, 'w') as file:
        json.dump(history, file, indent=4)

# Check if the input is a greeting
def is_greeting(text):
    greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon',
                 'good evening', 'good day', 'namaste', 'howdy', "what's up", 'how are you']
    return any(greet in text.lower() for greet in greetings)

# Generate a greeting response
def get_greeting_response():
    responses = [
        "Hello! How can I assist you today?",
        "Hi there! What would you like to ask?",
        "Hey! I'm here to help. What's on your mind?"
    ]
    return random.choice(responses)

# Function to call OpenAI API
def get_openai_response(messages):
    openai.api_key = OPENAI_API_KEY
    response = openai.ChatCompletion.create(
        model=MODEL_NAME,
        messages=[{"role": msg.role, "content": msg.content} for msg in messages]
    )
    return response["choices"][0]["message"]["content"]

# Initialize Streamlit app
st.set_page_config(page_title="Chatbot", page_icon="🤖", layout="wide")

# Initialize session state
if "history_data" not in st.session_state:
    st.session_state.history_data = load_conversation_history()
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    new_conversation = {"id": st.session_state.current_conversation_id, "messages": []}
    st.session_state.history_data["conversations"].append(new_conversation)
    save_conversation_history(st.session_state.history_data)

# Sidebar for conversation history
st.sidebar.title("Conversation History")
if st.sidebar.button("New Conversation"):
    st.session_state.current_conversation_id = str(uuid.uuid4())
    st.session_state.chat_history = []
    new_conversation = {"id": st.session_state.current_conversation_id, "messages": []}
    st.session_state.history_data["conversations"].append(new_conversation)
    save_conversation_history(st.session_state.history_data)
    st.rerun()

# Display past conversations
for conv in reversed(st.session_state.history_data["conversations"]):
    if st.sidebar.button(f"Conversation {conv['id'][:8]}", key=conv['id']):
        st.session_state.current_conversation_id = conv["id"]
        st.session_state.chat_history = conv["messages"]
        st.rerun()

# Main chat area
st.title("Chatbot")
st.markdown("Ask me anything!")

# Display chat history
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# User input
user_query = st.chat_input("Type your question here...")
if user_query:
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    
    # Greeting detection
    if is_greeting(user_query):
        response = get_greeting_response()
    else:
        # Use OpenAI API for response
        messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.chat_history]
        response = get_openai_response(messages)
    
    with st.chat_message("assistant"):
        st.write(response)
    st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Save conversation
    for conv in st.session_state.history_data["conversations"]:
        if conv["id"] == st.session_state.current_conversation_id:
            conv["messages"] = st.session_state.chat_history
            save_conversation_history(st.session_state.history_data)
            break
