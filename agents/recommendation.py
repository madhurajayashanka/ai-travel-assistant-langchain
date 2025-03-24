from utils.api_utils import (
    call_openai_api, 
    geocode_location, 
    get_places_nearby, 
    get_location_data
)
from utils.prompt_templates import (
    ITINERARY_CREATION_TEMPLATE, 
    CONTEXT_AWARE_TEMPLATE,
    BUDGET_OPTIMIZATION_TEMPLATE
)

class RecommendationAgent:
    """
    Generates travel recommendations and itineraries.
    Uses OpenAI to create comprehensive suggestions.
    """
    
    def __init__(self):
        self.progress_logs = []
    
    def log_progress(self, message):
        """Log progress message and store in progress logs."""
        self.progress_logs.append(message)
        print(f"[RecommendationAgent] {message}")
        
    def get_progress_logs(self):
        """Get all progress logs and clear the log."""
        logs = self.progress_logs.copy()
        self.progress_logs = []
        return logs
    
    def create_itinerary(self, destination, start_date, end_date, budget, interests, travel_style):
        """Create a complete itinerary based on user preferences."""
        self.log_progress(f"Starting to create itinerary for {destination}")
        
        # Format the prompt using the template
        prompt = ITINERARY_CREATION_TEMPLATE.format(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            interests=interests,
            travel_style=travel_style
        )
        
        self.log_progress("Generating initial itinerary...")
        
        # Generate the initial itinerary
        itinerary_text = call_openai_api(
            prompt=prompt,
            system_prompt="You are an expert travel planner. Create detailed, practical itineraries.",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=2000,
            progress_callback=self.log_progress
        )
        
        self.log_progress("Initial itinerary created successfully")
        
        # Enhance with real place data
        self.log_progress("Enhancing itinerary with detailed location information...")
        enhanced_itinerary = self._enhance_with_place_data(itinerary_text, destination)
        
        self.log_progress("Itinerary enhancement completed")
        
        return enhanced_itinerary
    
    def _enhance_with_place_data(self, itinerary_text, destination):
        """Enhance the itinerary with place data from OpenAI."""
        self.log_progress(f"Gathering detailed information about {destination}...")
        
        # Get location data using OpenAI
        location_data = get_location_data(destination, progress_callback=self.log_progress)
        
        if "error" in location_data:
            self.log_progress(f"Error getting location data: {location_data['error']}")
            return itinerary_text
        
        try:
            # Extract attraction and restaurant names
            attraction_names = [attraction.get("name", "") for attraction in location_data.get("attractions", [])]
            restaurant_names = [restaurant.get("name", "") for restaurant in location_data.get("restaurants", [])]
            
            self.log_progress(f"Found {len(attraction_names)} attractions and {len(restaurant_names)} restaurants")
            
            # Create a prompt to enhance the itinerary with real place names
            enhancement_prompt = f"""
            I have an itinerary for {destination}:
            
            {itinerary_text}
            
            I also have information about real attractions and restaurants in this area:
            
            Attractions: {', '.join(attraction_names[:10])}
            Restaurants: {', '.join(restaurant_names[:10])}
            
            Weather: {location_data.get('weather', 'Information not available')}
            Transportation: {location_data.get('transportation', 'Information not available')}
            
            Please enhance the itinerary by incorporating these real place names and information where appropriate, 
            but only if they fit the user's interests and preferences. Don't force them in if they don't fit.
            Keep the same format and structure of the original itinerary.
            """
            
            self.log_progress("Creating enhanced itinerary with real place names...")
            
            # Generate the enhanced itinerary
            enhanced_itinerary = call_openai_api(
                prompt=enhancement_prompt,
                system_prompt="You enhance travel itineraries with real location data. Keep the same format and structure.",
                model="gpt-3.5-turbo",
                temperature=0.5,
                max_tokens=2000,
                progress_callback=self.log_progress
            )
            
            return enhanced_itinerary
        
        except Exception as e:
            self.log_progress(f"Error enhancing itinerary: {e}")
            return itinerary_text
    
    def update_recommendations(self, itinerary, current_location=None, weather=None, local_events=None, time_of_day=None):
        """Update recommendations based on real-time context."""
        # Skip if no context information is provided
        if not any([current_location, weather, local_events, time_of_day]):
            return itinerary
        
        # Format the prompt using the template
        prompt = CONTEXT_AWARE_TEMPLATE.format(
            itinerary=itinerary,
            current_location=current_location or "Unknown",
            weather=weather or "Unknown",
            local_events=local_events or "None known",
            time_of_day=time_of_day or "Unknown"
        )
        
        # Generate updated recommendations
        updated_recommendations = call_openai_api(
            prompt=prompt,
            system_prompt="You are a real-time travel assistant. Update itineraries based on current conditions.",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1500
        )
        
        return updated_recommendations
    
    def optimize_budget(self, itinerary, strict_budget):
        """Optimize an itinerary for a stricter budget."""
        # Format the prompt using the template
        prompt = BUDGET_OPTIMIZATION_TEMPLATE.format(
            itinerary=itinerary,
            strict_budget=strict_budget
        )
        
        # Generate budget-optimized recommendations
        budget_optimized = call_openai_api(
            prompt=prompt,
            system_prompt="You are a budget travel expert. Optimize itineraries to reduce costs.",
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1500
        )
        
        return budget_optimized
    
    def get_place_recommendations(self, destination, interest_type, limit=5):
        """Get specific place recommendations by interest type."""
        self.log_progress(f"Finding {interest_type} recommendations for {destination}...")
        
        # Map interest types to place types
        place_type_mapping = {
            "food": "restaurants",
            "history": "historical sites and museums",
            "nature": "parks and natural attractions",
            "shopping": "shopping areas and markets",
            "nightlife": "nightlife venues and entertainment",
            "culture": "cultural sites and art galleries",
            "relaxation": "spas and relaxation spots"
        }
        
        # Get the appropriate place type
        place_type = place_type_mapping.get(interest_type.lower(), "tourist attractions")
        
        # Geocode the destination
        geocode_result = geocode_location(destination, progress_callback=self.log_progress)
        
        if "error" in geocode_result:
            self.log_progress(f"Error geocoding destination: {geocode_result['error']}")
            return []
            
        try:
            # Extract location data
            location = geocode_result.get("results", [{}])[0].get("geometry", {}).get("location", {})
            
            if not location:
                self.log_progress("Could not find location coordinates")
                return []
                
            lat, lng = location.get("lat"), location.get("lng")
            
            if not (lat and lng):
                self.log_progress("Invalid location coordinates")
                return []
                
            # Get specific places
            self.log_progress(f"Finding {place_type} near {destination}...")
            
            places_result = get_places_nearby(
                lat, lng, 
                radius=5000, 
                place_type=place_type,
                progress_callback=self.log_progress
            )
            
            # Extract place details
            place_results = places_result.get("results", [])
            self.log_progress(f"Found {len(place_results)} {place_type}")
            
            detailed_places = []
            for i, place in enumerate(place_results[:limit]):
                detailed_places.append({
                    "name": place.get("name", ""),
                    "address": f"{destination}",
                    "rating": "Not available",
                    "types": [place.get("type", place_type)],
                    "description": place.get("description", ""),
                    "website": "Not available"
                })
            
            return detailed_places
            
        except Exception as e:
            self.log_progress(f"Error getting place recommendations: {e}")
            return []