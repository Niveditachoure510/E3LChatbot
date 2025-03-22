import streamlit as st
import json
import os
import uuid
import random
from datetime import datetime
import requests
import time  # For loading animation

# Class to represent chat messages
class ChatMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content

# Constants for storage and API credentials
HISTORY_FILE = "conversation_history.json"
MISTRAL_API_KEY = "Bzkye1eO2xkBUaWxf0pSHWSKAcf39A6T"  # Replace with actual API key
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Load conversation history


def load_conversation_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {"conversations": []}  # Return empty if file is corrupt
    return {"conversations": []}

# Save conversation history
def save_conversation_history(history):
    with open(HISTORY_FILE, 'w') as file:
        json.dump(history, file, indent=4)

# Clear all conversation history
def clear_conversation_history():
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
    st.session_state.history_data = {"conversations": []}
    st.session_state.current_conversation_id = None
    st.session_state.chat_history = []
    st.rerun()

# Check if input is a greeting
def is_greeting(text):
    greetings = ['hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening', 'namaste']
    return any(greet in text.lower() for greet in greetings)

# Random greeting response
def get_greeting_response():
    responses = [
        "Hello! How can I assist you today?",
        "Hi there! What would you like to ask?",
        "Hey! I'm here to help. What's on your mind?"
    ]
    return random.choice(responses)

# Get AI response from Mistral API
def get_mistral_response(messages):
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    data = {
        "model": "mistral-tiny",
        "messages": [{"role": msg.role, "content": msg.content} for msg in messages]
    }
    response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Error: No response received.")
    return "Error: Unable to fetch response from Mistral API."

# Streamlit page configuration
st.set_page_config(page_title="Chatbot", page_icon="🤖", layout="wide")

# Initialize session state variables
if "history_data" not in st.session_state:
    st.session_state.history_data = load_conversation_history()
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
    st.session_state.chat_history = []
    st.session_state.conversation_topic = "New Conversation"

# Sidebar - Conversation History
st.sidebar.title("Conversation History")

# Start a new conversation
if st.sidebar.button("New Conversation"):
    new_id = str(uuid.uuid4())
    st.session_state.current_conversation_id = new_id
    st.session_state.chat_history = []
    st.session_state.conversation_topic = "New Conversation"
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_conversation = {
        "id": new_id,
        "title": st.session_state.conversation_topic,
        "date": current_time,
        "messages": []
    }
    st.session_state.history_data["conversations"].append(new_conversation)
    save_conversation_history(st.session_state.history_data)
    st.rerun()

# Clear all history
if st.sidebar.button("Clear All History"):
    clear_conversation_history()

# Load previous conversations
for conv in reversed(st.session_state.history_data["conversations"]):
    if st.sidebar.button(conv.get("title", "Untitled Conversation"), key=conv["id"]):
        st.session_state.current_conversation_id = conv["id"]
        st.session_state.chat_history = conv.get("messages", [])
        st.session_state.conversation_topic = conv["title"]
        st.rerun()

# Main Chat UI
st.title("Chatbot")
st.markdown("Ask me anything!")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

user_query = st.chat_input("Type your question here...")
if user_query:
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    
    # Update conversation title based on first user input
    if len(st.session_state.chat_history) == 1:
        st.session_state.conversation_topic = user_query[:30]  # Limit title length
        for conv in st.session_state.history_data["conversations"]:
            if conv["id"] == st.session_state.current_conversation_id:
                conv["title"] = st.session_state.conversation_topic
                break
        save_conversation_history(st.session_state.history_data)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... 🤔"):  # Animated loading sign
            time.sleep(1.5)  # Simulate loading
            if is_greeting(user_query):
                response = get_greeting_response()
            else:
                messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.chat_history]
                response = get_mistral_response(messages)
            st.write(response)

    st.session_state.chat_history.append({"role": "assistant", "content": response})

    # Update chat history in saved conversations
    for conv in st.session_state.history_data["conversations"]:
        if conv["id"] == st.session_state.current_conversation_id:
            conv["messages"] = st.session_state.chat_history
            save_conversation_history(st.session_state.history_data)
            break

    st.rerun()
