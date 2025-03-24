from utils.api_utils import call_openai_api, geocode_location
from utils.prompt_templates import TRANSLATION_TEMPLATE, ACCESSIBILITY_TEMPLATE

class ContextAgent:
    """
    Processes contextual information to enhance recommendations.
    Handles localization, translation, accessibility concerns, etc.
    """
    
    def __init__(self):
        pass
    
    def translate_content(self, content, target_language):
        """Translate content to the user's preferred language."""
        # Skip if target language is English (default)
        if target_language.lower() in ["english", "en"]:
            return content
            
        # Format the prompt using the template
        prompt = TRANSLATION_TEMPLATE.format(
            content=content,
            target_language=target_language
        )
        
        # Generate the translation
        translated_content = call_openai_api(
            prompt=prompt,
            system_prompt="You are a skilled translator. Provide accurate translations while maintaining meaning.",
            model="gpt-3.5-turbo",
            temperature=0.3,
            max_tokens=1500
        )
        
        return translated_content
    
    def adapt_for_accessibility(self, itinerary, accessibility_needs):
        """Modify recommendations to accommodate accessibility needs."""
        # Skip if no accessibility needs are specified
        if not accessibility_needs:
            return itinerary
            
        # Format the prompt using the template
        prompt = ACCESSIBILITY_TEMPLATE.format(
            itinerary=itinerary,
            accessibility_needs=accessibility_needs
        )
        
        # Generate accessibility-adapted recommendations
        adapted_itinerary = call_openai_api(
            prompt=prompt,
            system_prompt="You are an accessibility expert for travelers. Provide helpful adaptations.",
            model="gpt-3.5-turbo",
            temperature=0.5,
            max_tokens=1500
        )
        
        return adapted_itinerary
    
    def get_weather_info(self, location):
        """
        Get current weather information for a location.
        
        Note: This is a placeholder. In a production environment, you would
        integrate with a weather API. For cost optimization, we're using
        a simple response based on the location name.
        """
        # In a real implementation, you would call a weather API here
        # For this example, we'll return a placeholder
        return {
            "temperature": "22°C",
            "conditions": "Partly cloudy",
            "precipitation": "10% chance of rain"
        }
    
    def get_local_events(self, location, date):
        """
        Get information about local events at a destination.
        
        Note: This is a placeholder. In a production environment, you would
        integrate with an events API. For cost optimization, we're returning
        a simple response.
        """
        # In a real implementation, you would call an events API here
        # For this example, we'll use OpenAI to generate plausible events
        
        prompt = f"""
        Generate 3 plausible local events that might be happening in {location} on {date}.
        Include the event name, brief description, and location.
        Format as a JSON array of objects with fields: name, description, venue.
        Make these sound realistic and specific to {location}.
        """
        
        events_json = call_openai_api(
            prompt=prompt,
            system_prompt="You generate plausible local event information. Respond only with valid JSON.",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=500
        )
        
        # Try to parse the JSON, return empty list on failure
        try:
            # Clean up the response to extract just the JSON
            if "```json" in events_json:
                json_str = events_json.split("```json")[1].split("```")[0].strip()
            elif "```" in events_json:
                json_str = events_json.split("```")[1].strip()
            else:
                json_str = events_json.strip()
                
            import json
            events = json.loads(json_str)
            return events
        except:
            return []