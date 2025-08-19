import os
from flask import Flask, render_template, request, jsonify
from utils.chatbot_logic import get_initial_greeting, process_user_message

app = Flask(__name__)

# Set the secret key for session management
app.secret_key = os.urandom(24)

# In-memory chat history (for a single user session)
chat_history = []

@app.route('/')
def index():
    """
    Renders the main chat page and initializes the conversation.
    """
    initial_greeting = get_initial_greeting()
    # Clear history for a new session and add the first greeting
    chat_history.clear()
    chat_history.append({"role": "assistant", "content": initial_greeting})
    return render_template('index.html', initial_greeting=initial_greeting)

@app.route('/chat', methods=['POST'])
def chat():
    """
    Handles the incoming user message, gets a response from the chatbot logic,
    and returns it as JSON.
    """
    try:
        user_message = request.json.get('message')
        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Add user message to history
        chat_history.append({"role": "user", "content": user_message})

        # Get the chatbot's response
        bot_response = process_user_message(user_message, chat_history)

        # Add bot response to history
        chat_history.append({"role": "assistant", "content": bot_response})

        return jsonify({"response": bot_response})

    except Exception as e:
        print(f"An error occurred in /chat endpoint: {e}")
        error_message = "I'm sorry, I encountered a technical issue. Please try again later."
        chat_history.append({"role": "assistant", "content": error_message})
        return jsonify({"response": error_message}), 500

if __name__ == '__main__':
    app.run(debug=True)