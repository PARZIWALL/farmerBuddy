import os
import google.generativeai as genai
from utils.data_retrieval import get_weather_data, get_soil_data, get_mandi_prices
from utils.prompts import get_main_prompt

# --- Gemini API Configuration ---
GEMINI_API_KEY = "your gemini api"
model = None

# Configure Gemini API
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')  # Updated to newer model
        print("--- Gemini API configured successfully! ---")
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
else:
    print("CRITICAL: GEMINI_API_KEY not found.")

def get_initial_greeting():
    """Returns the initial greeting message for the chatbot."""
    return "Hello! I am your AI Farming Assistant, Krishi Mitra. How can I help you maximize your farm's potential today? Please tell me about your location and crop."

def process_user_message(user_message, chat_history):
    """
    Processes the user's message, gathers real-time data, and gets a response from the Gemini API.
    """
    if not model:
        return "I'm sorry, the AI model is not configured. Please check the server logs for an API key issue."

    try:
        # Extract location from user message or use default
        location = "Kanpur, Uttar Pradesh"
        
        print(f"Fetching real-time data for {location}...")
        weather_data = get_weather_data(location)
        soil_data = get_soil_data(location)
        mandi_prices = get_mandi_prices(crop="Wheat", state="Uttar Pradesh")

        full_prompt = get_main_prompt(
            user_query=user_message,
            chat_history=chat_history[:-1],  # Exclude current user message from history
            weather_data=weather_data,
            soil_data=soil_data,
            mandi_prices=mandi_prices
        )

        print("--- Sending Prompt to Gemini API ---")
        
        # Configure safety settings for agricultural content
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_MEDIUM_AND_ABOVE"
            }
        ]
        
        response = model.generate_content(
            full_prompt,
            safety_settings=safety_settings,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
        )
        
        if response.text:
            bot_response = response.text
        else:
            bot_response = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."

        return bot_response

    except Exception as e:
        print(f"Error processing message with Gemini: {e}")
        return "I'm sorry, I'm having trouble connecting to my knowledge base. Please try again with a different question."