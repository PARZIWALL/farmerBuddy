import requests
import json

# Weather API configuration
WEATHER_API_KEY = "openweather api"

def get_weather_data(location):
    """
    Fetches weather forecast data for a given location using OpenWeatherMap API.
    Falls back to mock data if API fails.
    """
    try:
        # Clean location name for API call
        location_clean = location.split(',')[0].strip()
        url = f"http://api.openweathermap.org/data/2.5/weather?q={location_clean}&appid={WEATHER_API_KEY}&units=metric"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract relevant information
        weather_info = {
            "location": data["name"],
            "temperature": f"{data['main']['temp']:.1f}°C",
            "feels_like": f"{data['main']['feels_like']:.1f}°C",
            "humidity": f"{data['main']['humidity']}%",
            "description": data["weather"][0]["description"].title(),
            "wind_speed": f"{data['wind']['speed']} m/s",
            "pressure": f"{data['main']['pressure']} hPa",
            "recommendation": generate_weather_recommendation(data)
        }
        
        return weather_info
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data: {e}")
        return get_mock_weather_data(location)
    except Exception as e:
        print(f"Error processing weather data: {e}")
        return get_mock_weather_data(location)

def generate_weather_recommendation(weather_data):
    """Generate farming recommendations based on weather data."""
    temp = weather_data['main']['temp']
    humidity = weather_data['main']['humidity']
    description = weather_data['weather'][0]['description']
    
    recommendations = []
    
    if temp > 35:
        recommendations.append("High temperature - ensure adequate irrigation")
    elif temp < 10:
        recommendations.append("Low temperature - protect crops from frost")
    
    if humidity > 80:
        recommendations.append("High humidity - monitor for fungal diseases")
    elif humidity < 30:
        recommendations.append("Low humidity - increase irrigation frequency")
    
    if "rain" in description.lower():
        recommendations.append("Rain expected - ensure proper drainage")
    
    return ". ".join(recommendations) if recommendations else "Weather conditions are favorable for farming activities"

def get_mock_weather_data(location):
    """Returns mock weather data when API is unavailable."""
    return {
        "location": location,
        "temperature": "28-35°C",
        "humidity": "75%",
        "description": "Partly Cloudy",
        "precipitation_chance": "High (80%) in the next 48 hours",
        "wind_speed": "15 kph",
        "recommendation": "High humidity and upcoming rain suggest being prepared for fungal diseases. Ensure good drainage."
    }

def get_soil_data(location):
    """
    Fetches soil analysis data for a given location.
    Currently returns mock data - can be integrated with soil health APIs.
    """
    # Mock data based on typical soil conditions in different regions
    soil_types = {
        "kanpur": {
            "soil_type": "Alluvial Loam",
            "ph_level": 7.2,
            "organic_carbon_percentage": 0.6,
            "nitrogen": "Medium",
            "phosphorus": "Low",
            "potassium": "High"
        },
        "default": {
            "soil_type": "Mixed Loam",
            "ph_level": 6.8,
            "organic_carbon_percentage": 0.5,
            "nitrogen": "Medium",
            "phosphorus": "Medium",
            "potassium": "Medium"
        }
    }
    
    location_key = location.lower().split(',')[0].strip()
    soil_info = soil_types.get(location_key, soil_types["default"])
    
    # Generate recommendation based on soil data
    recommendations = []
    if soil_info["ph_level"] > 7.5:
        recommendations.append("Soil is alkaline - consider adding organic matter")
    elif soil_info["ph_level"] < 6.0:
        recommendations.append("Soil is acidic - consider liming")
    
    if soil_info["phosphorus"] == "Low":
        recommendations.append("Low phosphorus - consider adding DAP or bone meal")
    if soil_info["nitrogen"] == "Low":
        recommendations.append("Low nitrogen - consider adding urea or compost")
    
    soil_info["recommendation"] = ". ".join(recommendations) if recommendations else "Soil conditions are well-balanced"
    
    return soil_info

def get_mandi_prices(crop="Wheat", state="Uttar Pradesh"):
    """
    Fetches current market (mandi) prices for a crop in a state.
    Currently returns mock data - can be integrated with government APIs.
    """
    # Mock price data for different crops and states
    price_data = {
        "wheat": {
            "uttar pradesh": [
                {"mandi_name": "Kanpur (Grain)", "modal_price_rs_per_quintal": 2150},
                {"mandi_name": "Lucknow", "modal_price_rs_per_quintal": 2125},
                {"mandi_name": "Unnao", "modal_price_rs_per_quintal": 2100}
            ],
            "maharashtra": [
                {"mandi_name": "Mumbai", "modal_price_rs_per_quintal": 2200},
                {"mandi_name": "Pune", "modal_price_rs_per_quintal": 2180},
                {"mandi_name": "Nashik", "modal_price_rs_per_quintal": 2160}
            ],
            "punjab": [
                {"mandi_name": "Amritsar", "modal_price_rs_per_quintal": 2250},
                {"mandi_name": "Ludhiana", "modal_price_rs_per_quintal": 2230},
                {"mandi_name": "Jalandhar", "modal_price_rs_per_quintal": 2210}
            ]
        },
        "rice": {
            "uttar pradesh": [
                {"mandi_name": "Kanpur", "modal_price_rs_per_quintal": 1850},
                {"mandi_name": "Lucknow", "modal_price_rs_per_quintal": 1875},
                {"mandi_name": "Varanasi", "modal_price_rs_per_quintal": 1900}
            ],
            "west bengal": [
                {"mandi_name": "Kolkata", "modal_price_rs_per_quintal": 1950},
                {"mandi_name": "Burdwan", "modal_price_rs_per_quintal": 1925},
                {"mandi_name": "Murshidabad", "modal_price_rs_per_quintal": 1900}
            ],
            "punjab": [
                {"mandi_name": "Amritsar", "modal_price_rs_per_quintal": 2000},
                {"mandi_name": "Ludhiana", "modal_price_rs_per_quintal": 1980},
                {"mandi_name": "Patiala", "modal_price_rs_per_quintal": 1960}
            ]
        }
    }
    
    crop_key = crop.lower()
    state_key = state.lower()
    
    if crop_key in price_data and state_key in price_data[crop_key]:
        prices = price_data[crop_key][state_key]
        
        # Find best price
        best_price = max(prices, key=lambda x: x["modal_price_rs_per_quintal"])
        
        prices.append({
            "recommendation": f"{best_price['mandi_name']} is currently offering the highest price at ₹{best_price['modal_price_rs_per_quintal']}/quintal. Consider transportation costs before making a decision."
        })
        
        return prices
    else:
        # Default prices
        return [
            {"mandi_name": "Local Market", "modal_price_rs_per_quintal": 2000},
            {"recommendation": "Prices are indicative. Check with local mandis for current rates."}
        ]