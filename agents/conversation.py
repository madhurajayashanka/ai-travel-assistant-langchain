from utils.api_utils import call_openai_api
from utils.prompt_templates import TRAVEL_ASSISTANT_SYSTEM_PROMPT

class ConversationAgent:
    """
    Handles natural language conversation with users.
    Functions as the main interface for user interactions.
    """
    
    def __init__(self, session_state=None):
        self.system_prompt = TRAVEL_ASSISTANT_SYSTEM_PROMPT
        self.conversation_history = []
        self.session_state = session_state or {}
    
    def process_message(self, user_message):
        """Process a message from the user and generate a response."""
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": user_message})
        
        # Prepare the full conversation context
        conversation_context = self._prepare_conversation_context()
        
        # Call the API
        response = call_openai_api(
            prompt=conversation_context,
            system_prompt=self.system_prompt,
            model="gpt-3.5-turbo",
            temperature=0.7
        )
        
        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response})
        
        return response
    
    def _prepare_conversation_context(self):
        """Prepare the conversation context for the API call."""
        # For cost efficiency, limit the history to last 10 messages
        recent_history = self.conversation_history[-10:]
        
        # Format as a single string
        context = ""
        for message in recent_history:
            prefix = "User: " if message["role"] == "user" else "Assistant: "
            context += f"{prefix}{message['content']}\n\n"
        
        # Add user context if available
        if self.session_state.get("user_preferences"):
            context += f"\nUser Preferences: {self.session_state['user_preferences']}\n\n"
        
        context += "Assistant: "
        return context
    
    def extract_travel_preferences(self, user_message):
        """
        Extract travel preferences from a user message.
        Returns a dictionary of identified preferences.
        """
        # Formulate a prompt specifically for extracting structured information
        extraction_prompt = f"""
        Extract the following travel preferences from the user's message, if present:
        - Destination
        - Travel dates (start and end)
        - Budget level (low, medium, high)
        - Interests (e.g., history, food, nature)
        - Travel style (e.g., luxury, backpacking, family)
        
        User message: {user_message}
        
        Format the response as a JSON object with these fields. If information is not provided, use null for that field.
        """
        
        # Call the API in JSON mode to get structured data
        response = call_openai_api(
            prompt=extraction_prompt,
            system_prompt="You extract structured information from text. Respond only with valid JSON.",
            model="gpt-3.5-turbo",
            temperature=0.1
        )
        
        # Parse the response, handling potential errors
        try:
            # If the response includes the JSON in a code block, extract just the JSON
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].strip()
            else:
                json_str = response.strip()
                
            import json
            preferences = json.loads(json_str)
            return preferences
        except:
            # Fallback to a simpler approach if JSON parsing fails
            preferences = {}
            for line in response.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    preferences[key.strip().lower()] = value.strip()
            return preferences
    
    def clear_history(self):
        """Clear the conversation history."""
        self.conversation_history = []