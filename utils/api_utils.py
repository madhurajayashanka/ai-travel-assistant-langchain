import os
import json
import time
from dotenv import load_dotenv

# Try to import optional dependencies with graceful fallbacks
try:
    import tiktoken
    tiktoken_available = True
except ImportError:
    tiktoken_available = False
    print("WARNING: tiktoken module not found. Token counting will use approximation.")

try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False
    print("WARNING: OpenAI module not found. Please install it with: pip install openai")

from utils.cache_manager import CacheManager

# Load environment variables
load_dotenv()

# Initialize API clients
if openai_available:
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
else:
    openai_client = None

# Initialize cache manager
cache_manager = CacheManager()

def count_tokens(text, model="gpt-3.5-turbo"):
    """Count the number of tokens in a text string."""
    if tiktoken_available:
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fall back to approximation if encoding fails
            return len(text.split()) * 1.3  # Rough estimate
    else:
        # Fallback approximation when tiktoken is not available
        return len(text.split()) * 1.3  # Rough estimate

def optimize_prompt(prompt, max_tokens=4000):
    """Optimize a prompt to stay within token limits."""
    current_tokens = count_tokens(prompt)
    
    if current_tokens <= max_tokens:
        return prompt
    
    # Simple optimization - truncate and add note
    ratio = max_tokens / current_tokens
    words = prompt.split()
    new_length = int(len(words) * ratio) - 20  # Leave room for the note
    
    optimized_prompt = " ".join(words[:new_length])
    optimized_prompt += "\n\n[Note: The original prompt was truncated to fit within token limits.]"
    
    return optimized_prompt

def call_openai_api(prompt, system_prompt=None, model="gpt-3.5-turbo", temperature=0.7, max_tokens=1000, progress_callback=None):
    """Call the OpenAI API with caching and token optimization."""
    if not openai_available:
        return "ERROR: OpenAI module is not installed. Please run: pip install openai"
    
    if progress_callback:
        progress_callback("Preparing to call OpenAI API...")
        
    # Check cache first
    cache_key = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    cached_response = cache_manager.get_cached_response(cache_key, "openai")
    if cached_response:
        if progress_callback:
            progress_callback("Retrieved response from cache")
        return cached_response
    
    if progress_callback:
        progress_callback("Making API call to OpenAI...")
    
    # Prepare messages
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": prompt})
    
    # Count tokens to ensure we're within limits
    total_tokens = sum(count_tokens(msg["content"]) for msg in messages)
    
    if total_tokens > 4000:  # Adjust based on model limits
        if progress_callback:
            progress_callback("Optimizing prompt to fit within token limits...")
        # Optimize the user message (the prompt)
        messages[-1]["content"] = optimize_prompt(prompt, 4000 - count_tokens(system_prompt or ""))
    
    # Call API with exponential backoff for rate limits
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            if progress_callback and attempt > 0:
                progress_callback(f"Retrying API call (attempt {attempt+1}/{max_retries})...")
                
            response = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = response.choices[0].message.content
            
            # Cache the result
            cache_manager.cache_response(cache_key, result, "openai")
            
            if progress_callback:
                progress_callback("Successfully received response from OpenAI")
                
            return result
        
        except Exception as e:
            if progress_callback:
                progress_callback(f"Error: {str(e)}")
                
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                return f"Error: {str(e)}"

def get_location_data(location_name, progress_callback=None):
    """Get location information using OpenAI instead of Google Maps."""
    if progress_callback:
        progress_callback(f"Gathering information about {location_name}...")
    
    # Check cache first
    cache_key = {"location": location_name}
    cached_response = cache_manager.get_cached_response(cache_key, "location_data")
    if cached_response:
        if progress_callback:
            progress_callback(f"Retrieved {location_name} data from cache")
        return cached_response

    # Use OpenAI to get location information
    prompt = f"""
    I need detailed information about {location_name} as a travel destination. Please provide:
    
    1. A brief description of the location
    2. Popular attractions (at least 5-10)
    3. Notable restaurants or food options (at least 5-10)
    4. Best neighborhoods or areas to explore
    5. Typical weather patterns
    6. Local transportation options
    
    Format the response as a JSON object with these keys: description, attractions, restaurants, neighborhoods, weather, transportation.
    Each attraction and restaurant should be an object with name, description, and category fields.
    Ensure the JSON is valid and properly formatted.
    """
    
    result = call_openai_api(
        prompt=prompt,
        system_prompt="You are a knowledgeable travel guide with expertise in global destinations. Provide accurate, structured information about locations. Always respond with valid JSON.",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1500,
        progress_callback=progress_callback
    )
    
    try:
        # Extract JSON if it's in a code block
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].strip()
        else:
            json_str = result.strip()
            
        location_data = json.loads(json_str)
        
        # Cache the result
        cache_manager.cache_response(cache_key, location_data, "location_data", expire_hours=720)  # Cache for 30 days
        
        return location_data
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error parsing location data: {str(e)}")
        return {"error": str(e)}

def geocode_location(location_name, progress_callback=None):
    """Get location coordinates using OpenAI."""
    if progress_callback:
        progress_callback(f"Finding coordinates for {location_name}...")
    
    # Check cache first
    cache_key = {"geocode": location_name}
    cached_response = cache_manager.get_cached_response(cache_key, "geocode")
    if cached_response:
        if progress_callback:
            progress_callback(f"Retrieved coordinates from cache")
        return cached_response
    
    prompt = f"""
    I need the approximate latitude and longitude coordinates for {location_name}.
    Please provide only the coordinates in a valid JSON format with 'lat' and 'lng' fields.
    For example: {{"lat": 40.7128, "lng": -74.0060}} for New York City.
    Do not include any explanations, just the JSON object.
    """
    
    result = call_openai_api(
        prompt=prompt,
        system_prompt="You are a geographic information system. Provide accurate latitude and longitude coordinates for locations.",
        model="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=100,
        progress_callback=progress_callback
    )
    
    try:
        # Extract JSON if it's in a code block
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].strip()
        else:
            json_str = result.strip()
            
        coordinates = json.loads(json_str)
        
        # Format the result to match the expected structure from Google Maps
        geocode_result = {
            "results": [{
                "geometry": {
                    "location": coordinates
                }
            }],
            "status": "OK"
        }
        
        # Cache the result
        cache_manager.cache_response(cache_key, geocode_result, "geocode", expire_hours=720)  # Cache for 30 days
        
        return geocode_result
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error parsing geocode data: {str(e)}")
        return {"error": str(e), "results": [], "status": "ERROR"}

def get_places_nearby(lat, lng, radius=1500, place_type=None, progress_callback=None):
    """Get nearby places using OpenAI."""
    if progress_callback:
        progress_callback(f"Finding nearby places of type: {place_type or 'various'}...")
    
    # Check cache first
    cache_key = {"nearby": f"{lat},{lng}", "radius": radius, "type": place_type}
    cached_response = cache_manager.get_cached_response(cache_key, "places_nearby")
    if cached_response:
        if progress_callback:
            progress_callback(f"Retrieved nearby places from cache")
        return cached_response
    
    # Convert coordinates to approximate location name
    reverse_geocode_prompt = f"""
    Given the coordinates latitude {lat} and longitude {lng}, what is the name of this location?
    Provide only the name of the city or area, no additional information.
    """
    
    location_name = call_openai_api(
        prompt=reverse_geocode_prompt,
        system_prompt="You are a geographic information system. Provide accurate location names for coordinates.",
        model="gpt-3.5-turbo",
        temperature=0.1,
        max_tokens=50,
        progress_callback=progress_callback
    ).strip()
    
    # Now get places based on the location name and type
    type_description = place_type or "interesting places"
    
    places_prompt = f"""
    I need a list of {type_description} in or near {location_name}.
    
    Please provide at least 10 places with the following information for each:
    1. Name of the place
    2. Brief description (1-2 sentences)
    3. Category/type
    
    Format the response as a JSON array of objects with fields: name, description, type.
    Ensure the JSON is valid and properly formatted.
    """
    
    result = call_openai_api(
        prompt=places_prompt,
        system_prompt="You are a knowledgeable travel guide with expertise in global destinations. Provide accurate information about local attractions.",
        model="gpt-3.5-turbo",
        temperature=0.7,
        max_tokens=1000,
        progress_callback=progress_callback
    )
    
    try:
        # Extract JSON if it's in a code block
        if "```json" in result:
            json_str = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            json_str = result.split("```")[1].strip()
        else:
            json_str = result.strip()
            
        places = json.loads(json_str)
        
        # Format to match Google Maps API structure
        places_result = {
            "results": places,
            "status": "OK"
        }
        
        # Cache the result
        cache_manager.cache_response(cache_key, places_result, "places_nearby", expire_hours=168)  # Cache for 7 days
        
        return places_result
    except Exception as e:
        if progress_callback:
            progress_callback(f"Error parsing places data: {str(e)}")
        return {"error": str(e), "results": [], "status": "ERROR"}

def get_place_details(place_id, progress_callback=None):
    """Get place details using OpenAI."""
    # Since we're not using Google Maps, place_id isn't meaningful
    # We'll just return a basic structure with the name
    return {
        "result": {
            "name": place_id,
            "formatted_address": "Address information not available",
            "rating": "Not available",
            "types": [],
            "website": "Not available"
        }
    }