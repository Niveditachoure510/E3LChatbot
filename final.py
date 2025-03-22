import streamlit as st
import json
import uuid
import hashlib
import time
import random
import requests
from datetime import datetime
import mysql.connector

# Streamlit Page Configuration
st.set_page_config(page_title="Chatbot", page_icon="🤖", layout="wide")

# MySQL Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",  # Default password in XAMPP is empty
    "database": "chatbot_db"
}

# Initialize session state variables
if "history_data" not in st.session_state:
    st.session_state.history_data = {"conversations": []}
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "welcome_shown" not in st.session_state:
    st.session_state.welcome_shown = False

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to establish a database connection
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        st.error(f"Database connection error: {e}")
        return None

# Function to register a new user
def register_user(username, password):
    conn = get_db_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hash_password(password))
        )
        conn.commit()
        return True
    except mysql.connector.IntegrityError:
        st.error("❌ Username already exists. Please choose a different one.")
        return False
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Function to authenticate a user
def authenticate(username, password):
    conn = get_db_connection()
    if conn is None:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        if user_data and user_data[0] == hash_password(password):
            return True
        return False
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# Load conversation history from MySQL
def load_conversation_history(username):
    """
    Load conversation history for a specific user from the database.
    """
    conn = get_db_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        # Load conversations for the user
        query = "SELECT * FROM conversations WHERE username = %s ORDER BY date DESC"
        cursor.execute(query, (username,))
        conversations = cursor.fetchall()

        # Load chat history for each conversation
        for conv in conversations:
            query = """
            SELECT role, content FROM chat_history
            WHERE conversation_id = %s ORDER BY timestamp ASC
            """
            cursor.execute(query, (conv["id"],))
            messages = cursor.fetchall()
            conv["messages"] = messages

        return conversations
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Save Conversation History
def save_conversation_history(conversation):
    """
    Save a conversation to the conversations table in the database.
    """
    # Debug: Print the conversation data
    print("DEBUG: Saving conversation ->", conversation)

    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO conversations (id, username, title, date, messages)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE messages = VALUES(messages)
        """
        cursor.execute(query, (
            conversation["id"],
            conversation["username"],
            conversation["title"],
            conversation["date"],
            json.dumps(conversation["messages"])  # Convert list to JSON format
        ))
        conn.commit()
        print("DEBUG: Conversation saved successfully!")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

# Clear conversation history from MySQL
def clear_conversation_history():
    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    try:
        query = "DELETE FROM conversations WHERE username = %s"
        cursor.execute(query, (st.session_state.username,))
        conn.commit()
        st.session_state.history_data = {"conversations": []}
        st.session_state.current_conversation_id = None
        st.session_state.chat_history = []
        st.rerun()
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

# Function to save a message to the database
def save_message_to_db(conversation_id, username, role, content):
    """
    Save a message to the chat_history table in the database.
    """
    # Debug: Print the message data
    print("DEBUG: Saving message ->", conversation_id, username, role, content)

    conn = get_db_connection()
    if conn is None:
        return
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO chat_history (conversation_id, username, role, content)
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (conversation_id, username, role, content))
        conn.commit()
        print("DEBUG: Message saved successfully!")
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
    finally:
        cursor.close()
        conn.close()

# Function to load chat history from the database
def load_chat_history(conversation_id):
    conn = get_db_connection()
    if conn is None:
        return []
    cursor = conn.cursor(dictionary=True)
    try:
        query = """
        SELECT role, content FROM chat_history 
        WHERE conversation_id = %s ORDER BY timestamp ASC
        """
        cursor.execute(query, (conversation_id,))
        messages = cursor.fetchall()
        return messages
    except mysql.connector.Error as e:
        st.error(f"Database error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

# Constants
MISTRAL_API_KEY = "Bzkye1eO2xkBUaWxf0pSHWSKAcf39A6T"  # Replace with your actual API key
MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"

# Function to get AI response
def get_mistral_response(messages):
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}"}
    data = {"model": "mistral-tiny", "messages": messages}
    try:
        response = requests.post(MISTRAL_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            raw_response = response.json().get("choices", [{}])[0].get("message", {}).get("content", "Error: No response received.")
            prompts = [
                "Sure, here's what I found:",
                "That's a great question!",
                "Let me break it down for you:",
                "Here's an insightful take on that:",
                "Let's explore this together:",
                "Certainly!",
                "Absolutely, here’s what I can tell you:"
            ]
            return f"{random.choice(prompts)}\n{raw_response}"
        else:
            return "I couldn't fetch a response at the moment. Please try again later."
    except requests.exceptions.RequestException:
        return "Error: Unable to connect to the AI service."

# Display login/signup page if not logged in
if not st.session_state.logged_in:
    st.title("🔐 Login or Signup")
    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        st.subheader("Login")
        login_username = st.text_input("Username", key="login_username")
        login_password = st.text_input("Password", type="password", key="login_password")
        remember_me = st.checkbox("Remember Me")
        if st.button("Login"):
            if authenticate(login_username, login_password):
                # Set session state variables
                st.session_state.logged_in = True
                st.session_state.username = login_username

                # Load user-specific chat history from the database
                st.session_state.history_data = {"conversations": load_conversation_history(login_username)}
                st.session_state.chat_history = []
                st.session_state.current_conversation_id = None

                # If there are previous conversations, load the latest one
                if st.session_state.history_data["conversations"]:
                    latest_conversation = st.session_state.history_data["conversations"][0]
                    st.session_state.current_conversation_id = latest_conversation["id"]
                    st.session_state.chat_history = latest_conversation.get("messages", [])
                    st.session_state.conversation_topic = latest_conversation["title"]
                else:
                    st.session_state.chat_history = []  # Initialize to empty list if no conversations exist

                # Debug statements
                print("DEBUG: Current conversation ID ->", st.session_state.current_conversation_id)
                print("DEBUG: Chat history ->", st.session_state.chat_history)

                st.success("✅ Login successful! Redirecting...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
        if st.button("Forgot Password?"):
            st.info("Please contact support to reset your password.")

    with tab2:
        st.subheader("Signup")
        signup_username = st.text_input("Choose a Username", key="signup_username")
        signup_password = st.text_input("Choose a Password", type="password", key="signup_password")
        
        # Basic password strength check
        if signup_password:
            if len(signup_password) < 8:
                st.warning("⚠️ Password must be at least 8 characters long.")
            else:
                st.success("✅ Password is strong enough.")

        if st.button("Signup"):
            if len(signup_password) < 8:
                st.error("❌ Password must be at least 8 characters long.")
            else:
                if register_user(signup_username, signup_password):
                    st.success("✅ Signup successful! Please login.")
                else:
                    st.error("❌ Signup failed. Please try again.")

    st.stop()  # Stop execution if not logged in

# After login, show welcome message
if not st.session_state.welcome_shown:
    st.toast("You're successfully logged in.")
    st.toast(f"🎉 Welcome, {st.session_state.username}!", icon="✅")
    st.session_state.welcome_shown = True

# Test database connection
conn = get_db_connection()
if conn and conn.is_connected():
    st.success("✅ Database Connection Successful!")
    conn.close()
else:
    st.error("❌ Database Connection Failed!")

# Sidebar: Logout Button
if st.sidebar.button("🔒 Logout", key="logout_button"):
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.history_data = {"conversations": []}
    st.session_state.chat_history = []
    st.session_state.current_conversation_id = None
    st.rerun()

# Sidebar: Conversation History
st.sidebar.title("📜 Conversation History")

# New Conversation Button
if st.sidebar.button("➕ New Conversation"):
    st.session_state.current_conversation_id = None
    st.session_state.chat_history = []
    st.session_state.conversation_topic = None
    st.rerun()

# Clear All History Button
if st.sidebar.button("🗑️ Clear All History"):
    clear_conversation_history()

# Sidebar: Conversation History with Date and Delete Option
for conv in reversed(st.session_state.history_data["conversations"]):
    with st.sidebar.expander(f"{conv.get('title', 'Untitled Conversation')} - {conv['date']}"):
        if st.button("Load", key=f"load_{conv['id']}"):
            st.session_state.current_conversation_id = conv["id"]
            st.session_state.chat_history = conv.get("messages", [])
            st.session_state.conversation_topic = conv["title"]
            st.rerun()
        
        if st.button("Delete", key=f"delete_{conv['id']}"):
            st.session_state.history_data["conversations"] = [
                c for c in st.session_state.history_data["conversations"] if c["id"] != conv["id"]
            ]
            save_conversation_history(st.session_state.history_data)
            st.rerun()

# Chat UI
st.title(f"🤖 AI Chatbot - {st.session_state.username}")
st.markdown("Ask me anything!")

# Quick Questions Section
st.subheader("Quick Questions")
prebuilt_questions = [
    "How do I start a career in AI and Machine Learning?",
    "What are the latest trends in software development?",
    "How can I transition from a non-tech to a tech career?",
    "How to get started with Data Engineering?",
    "How can I get an internship in software development?",
    "What are some common mistakes in technical interviews?",
    "How to negotiate a salary in the IT industry?",
]

with st.expander("Prebuilt Questions"):
    for question in prebuilt_questions:
        if st.button(question):
            user_query = question
            break  # Exit the loop after selecting a question
    else:
        user_query = None  # No question selected

# Display chat history
if st.session_state.chat_history:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])  # Use "content" instead of "message"
else:
    st.info("No chat history available. Start a new conversation!")

# Chat input field
if user_query is None:  # Only check chat input if no prebuilt question is selected
    user_query = st.chat_input("Type your question here...")

# Handle user query and generate assistant response
if user_query:
    # If no conversation ID exists, create a new conversation
    if not st.session_state.current_conversation_id:
        new_id = str(uuid.uuid4())
        st.session_state.current_conversation_id = new_id
        st.session_state.chat_history = []
        st.session_state.conversation_topic = user_query[:30]

        new_conversation = {
            "id": new_id,
            "username": st.session_state.username,
            "title": st.session_state.conversation_topic,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "messages": []
        }
        st.session_state.history_data["conversations"].append(new_conversation)
        print("DEBUG: New conversation created ->", new_conversation)

    # Append user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    print("DEBUG: User message added to chat history ->", user_query)

    # Save user message in the database
    save_message_to_db(st.session_state.current_conversation_id, st.session_state.username, "user", user_query)

    # Generate assistant response
    with st.chat_message("assistant"):
        with st.spinner("Generating....⏳"):
            response = get_mistral_response(st.session_state.chat_history)
            st.write(response)

    # Append assistant response to chat history
    st.session_state.chat_history.append({"role": "assistant", "content": response})
    print("DEBUG: Assistant response added to chat history ->", response)

    # Save assistant response in the database
    save_message_to_db(st.session_state.current_conversation_id, st.session_state.username, "assistant", response)

    # Update conversation in history_data
    for conv in st.session_state.history_data["conversations"]:
        if conv["id"] == st.session_state.current_conversation_id:
            conv["messages"] = st.session_state.chat_history
            print("DEBUG: Updated conversation ->", conv)
            save_conversation_history(conv)  # Save to database
            break

    # Rerun to update the UI
    st.rerun()