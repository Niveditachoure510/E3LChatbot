from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import os
import uuid
import random
import requests

app = FastAPI()

# Constants
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
            return {"conversations": []}
    return {"conversations": []}

# Save conversation history
def save_conversation_history(history):
    with open(HISTORY_FILE, 'w') as file:
        json.dump(history, file, indent=4)

# Greeting detection
def is_greeting(text):
    greetings = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'namaste']
    return any(greet in text.lower() for greet in greetings)

# Greeting response
def get_greeting_response():
    responses = [
        "Hello! How can I assist you today?",
        "Hi there! What would you like to ask?",
        "Hey! I'm here to help. What's on your mind?"
    ]
    return random.choice(responses)

# Mistral API request
def get_mistral_response(messages):
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    data = {
        "model": "mistral-tiny",
        "messages": messages
    }
    response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json().get("choices", [{}])[0].get("message", {}).get("content", "Error: No response received.")
    return "Error: Unable to fetch response from Mistral API."

# Pydantic request model
class ChatRequest(BaseModel):
    conversation_id: str
    user_input: str

@app.post("/chat/")
def chat(request: ChatRequest):
    history = load_conversation_history()

    # Get or create conversation
    conversation = next((conv for conv in history["conversations"] if conv["id"] == request.conversation_id), None)
    if not conversation:
        conversation = {
            "id": request.conversation_id,
            "messages": []
        }
        history["conversations"].append(conversation)

    # User message
    conversation["messages"].append({"role": "user", "content": request.user_input})

    # AI Response
    if is_greeting(request.user_input):
        response_text = get_greeting_response()
    else:
        messages = [{"role": msg["role"], "content": msg["content"]} for msg in conversation["messages"]]
        response_text = get_mistral_response(messages)

    # Add assistant message
    conversation["messages"].append({"role": "assistant", "content": response_text})

    save_conversation_history(history)

    return {"response": response_text, "conversation_id": request.conversation_id}
