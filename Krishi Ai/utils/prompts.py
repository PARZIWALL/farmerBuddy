import json

def get_main_prompt(user_query, chat_history, weather_data, soil_data, mandi_prices):
    """
    Constructs the detailed, context-rich prompt for the Gemini API.
    """
    # Format the real-time data into a readable string for the AI
    context_data = f"""
**REAL-TIME AGRICULTURAL DATA:**

**Weather Information:**
{json.dumps(weather_data, indent=2)}

**Soil Analysis:**
{json.dumps(soil_data, indent=2)}

**Market Prices (Mandi Rates):**
{json.dumps(mandi_prices, indent=2)}
"""

    # Format chat history (limit to last 10 messages to avoid token overflow)
    recent_history = chat_history[-10:] if len(chat_history) > 10 else chat_history
    history_str = ""
    if recent_history:
        history_str = "\n".join([f"{msg['role'].title()}: {msg['content']}" for msg in recent_history])

    prompt = f"""You are "Krishi Mitra," an expert AI agricultural advisor specifically designed to help Indian farmers. You have deep expertise in:
- Crop cultivation and management
- Weather-based farming decisions
- Soil health and nutrition
- Market pricing and crop economics
- Pest and disease management
- Government schemes and subsidies
- Modern farming techniques

**YOUR RESPONSE GUIDELINES:**
1. **Be Practical & Actionable**: Provide specific, implementable advice
2. **Use Real-Time Data**: Base your recommendations on the provided weather, soil, and market data
3. **Be Conversational**: Write in a friendly, supportive tone
4. **Consider Local Context**: Focus on Indian farming conditions and practices
5. **Provide Value**: Don't just answer the question - anticipate next steps

{context_data}

**CONVERSATION HISTORY:**
{history_str}

**FARMER'S CURRENT QUESTION:** "{user_query}"

**YOUR EXPERT RESPONSE AS KRISHI MITRA:**"""

    return prompt