import streamlit as st
import json
import datetime
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
import os
from openai import OpenAI

# Import our modules
from agents.conversation import ConversationAgent
from agents.recommendation import RecommendationAgent
from agents.context import ContextAgent
from models import get_db_connection
from utils.api_utils import geocode_location

# Load environment variables
load_dotenv()

# Check if API keys are available
if not os.getenv("OPENAI_API_KEY"):
    st.error("Missing OpenAI API key. Please add your OpenAI API key to the .env file.")
    st.stop()

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = f"user_{random.randint(1000, 9999)}"
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'current_itinerary' not in st.session_state:
    st.session_state.current_itinerary = None
if 'current_itinerary_id' not in st.session_state:
    st.session_state.current_itinerary_id = None
if 'preferences' not in st.session_state:
    st.session_state.preferences = {}
if 'language' not in st.session_state:
    st.session_state.language = "English"
if 'progress_logs' not in st.session_state:
    st.session_state.progress_logs = []
# Add new session state for application logs
if 'app_logs' not in st.session_state:
    st.session_state.app_logs = []
if 'show_logs' not in st.session_state:
    st.session_state.show_logs = False

# Utility function for logging
def log_activity(message, level="INFO"):
    """Log an activity and display to user if enabled"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {"timestamp": timestamp, "level": level, "message": message}
    st.session_state.app_logs.append(log_entry)
    print(f"[{timestamp}] [{level}] {message}")
    
    # Keep only the most recent 100 logs
    if len(st.session_state.app_logs) > 100:
        st.session_state.app_logs = st.session_state.app_logs[-100:]

# Log application start
log_activity("Application started", "INFO")

# Initialize agents
conversation_agent = ConversationAgent(session_state=st.session_state)
recommendation_agent = RecommendationAgent()
context_agent = ContextAgent()

# Override recommendation agent log_progress method to use our logging system
original_log_progress = recommendation_agent.log_progress

def enhanced_log_progress(message):
    original_log_progress(message)
    log_activity(f"Recommendation: {message}")

recommendation_agent.log_progress = enhanced_log_progress

# Page layout and styling
st.set_page_config(page_title="AI Travel Assistant", page_icon="✈️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-top: 0;
        font-style: italic;
    }
    .section-header {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 20px;
        font-weight: bold;
        color: #1E88E5;
    }
    .info-box {
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .progress-container {
        margin-top: 10px;
        padding: 10px;
        border-radius: 5px;
        max-height: 200px;
        overflow-y: auto;
    }
    .progress-item {
        padding: 3px 0;
        border-bottom: 1px solid #eee;
        font-size: 0.9rem;
    }
    .log-container {
        margin-top: 10px;
        padding: 10px;
        border-radius: 5px;
        max-height: 300px;
        overflow-y: auto;
=        border: 1px solid #eee;
    }
    .log-entry {
        padding: 3px 5px;
        margin-bottom: 3px;
        font-family: monospace;
        font-size: 0.8rem;
        border-bottom: 1px solid #f0f0f0;
    }
    .log-timestamp {
        color: #666;
        margin-right: 5px;
    }
    .log-level-INFO {
        color: #1976D2;
    }
    .log-level-WARNING {
        color: #FF9800;
    }
    .log-level-ERROR {
        color: #D32F2F;
    }
    .log-level-SUCCESS {
        color: #388E3C;
    }
</style>
""", unsafe_allow_html=True)

# Page title and description
st.markdown("<h1 class='main-header'>AI Travel Assistant</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Your personalized travel planning companion</p>", unsafe_allow_html=True)

# Sidebar for user settings and preferences
with st.sidebar:
    st.markdown("<h2 class='section-header'>Settings</h2>", unsafe_allow_html=True)
    
    # Language selection
    language_options = ["English", "Spanish", "French", "German", "Italian", "Japanese", "Chinese", "Arabic"]
    selected_language = st.selectbox("Language", language_options, index=language_options.index(st.session_state.language))
    
    if selected_language != st.session_state.language:
        log_activity(f"Language changed from {st.session_state.language} to {selected_language}")
        st.session_state.language = selected_language
    
    # Accessibility needs
    st.markdown("<h3>Accessibility Preferences</h3>", unsafe_allow_html=True)
    accessibility_needs = st.text_area("Accessibility Needs (if any)", 
                                     placeholder="E.g., wheelchair accessible, visual impairments, etc.")
    
    # Model selection
    st.markdown("<h3>Model Settings</h3>", unsafe_allow_html=True)
    model_options = ["gpt-3.5-turbo", "gpt-4"]
    selected_model = st.selectbox("AI Model", model_options, index=0)
    
    # Save preferences button
    if st.button("Save Preferences", type="primary"):
        # Update user preferences in database
        log_activity("Saving user preferences to database")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR REPLACE INTO users (session_id, preferences, language) VALUES (?, ?, ?)",
            (st.session_state.user_id, json.dumps({"accessibility_needs": accessibility_needs, "model": selected_model}), selected_language)
        )
        
        conn.commit()
        conn.close()
        
        log_activity("User preferences saved successfully", "SUCCESS")
        st.success("Preferences saved!")
    
    # Activity Log Toggle
    st.markdown("<h3>Activity Log</h3>", unsafe_allow_html=True)
    show_logs = st.toggle("Show activity logs", value=st.session_state.show_logs)
    
    if show_logs != st.session_state.show_logs:
        st.session_state.show_logs = show_logs
        log_activity(f"Activity logs {'shown' if show_logs else 'hidden'}")
    
    # Display logs if enabled
    if st.session_state.show_logs:
        st.markdown("<div class='log-container'>", unsafe_allow_html=True)
        
        # Add a clear logs button
        if st.button("Clear Logs"):
            st.session_state.app_logs = []
            log_activity("Logs cleared")
            st.rerun()
            
        # Show the logs
        for log in reversed(st.session_state.app_logs):
            st.markdown(
                f"<div class='log-entry'>"
                f"<span class='log-timestamp'>{log['timestamp']}</span> "
                f"<span class='log-level-{log['level']}'>[{log['level']}]</span> "
                f"{log['message']}</div>", 
                unsafe_allow_html=True
            )
        st.markdown("</div>", unsafe_allow_html=True)

# Tabs for different functionalities
tab1, tab2, tab3 = st.tabs(["💬 Chat", "🗺️ Plan Your Trip", "📋 Current Itinerary"])

# Tab 1: Chat Interface
with tab1:
    st.markdown("<h2 class='section-header'>Chat with Your Travel Assistant</h2>", unsafe_allow_html=True)
    log_activity("Entered chat tab")
    
    # Info box
    with st.expander("Tips for using the chat", expanded=False):
        st.markdown("""
        - Ask about destinations you're interested in
        - Inquire about travel tips, best times to visit, or must-see attractions
        - Ask for budget-friendly options or luxury experiences
        - Share your preferences like "I love historical sites" or "I prefer outdoor activities"
        - Ask about specific activities like "What are good hiking spots in Bali?"
        """)
    
    # Chat container with improved styling
    chat_container = st.container()
    with chat_container:
        # Display conversation history
        for message in st.session_state.conversation_history:
            if message["role"] == "user":
                st.markdown(f"<div style=' padding: 10px; border-radius: 10px; margin-bottom: 10px;'><strong>You:</strong> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style=' padding: 10px; border-radius: 10px; margin-bottom: 10px;'><strong>Assistant:</strong> {message['content']}</div>", unsafe_allow_html=True)
    
    # User input
    user_message = st.text_input("Type your message...", key="chat_input", placeholder="Ask me anything about travel planning...")
    
    col1, col2 = st.columns([1, 5])
    with col1:
        send_button = st.button("Send", key="send_button", use_container_width=True)
    with col2:
        if st.button("Clear Chat", key="clear_chat", use_container_width=True):
            log_activity("Clearing chat history")
            conversation_agent.clear_history()
            st.session_state.conversation_history = []
            log_activity("Chat history cleared", "SUCCESS")
            st.rerun()
    
    if send_button or (user_message and len(user_message) > 0 and user_message[-1] == '\n'):
        if user_message:
            # Add user message to conversation history
            log_activity(f"Received user message: '{user_message[:30]}...' if len(user_message) > 30 else user_message")
            st.session_state.conversation_history.append({"role": "user", "content": user_message})
            
            # Show a spinner while processing
            with st.spinner("Thinking..."):
                # Extract travel preferences if present
                log_activity("Extracting travel preferences from message")
                extracted_prefs = conversation_agent.extract_travel_preferences(user_message)
                if extracted_prefs.get("destination"):
                    log_activity(f"Extracted destination: {extracted_prefs.get('destination')}")
                    st.session_state.preferences.update(extracted_prefs)
                
                # Get assistant response
                log_activity("Generating assistant response")
                response = conversation_agent.process_message(user_message)
                log_activity("Response generated successfully")
                
                # Translate if necessary
                if st.session_state.language != "English":
                    log_activity(f"Translating response to {st.session_state.language}")
                    with st.spinner(f"Translating to {st.session_state.language}..."):
                        response = context_agent.translate_content(response, st.session_state.language)
                    log_activity("Translation completed")
                
                # Add assistant response to conversation history
                st.session_state.conversation_history.append({"role": "assistant", "content": response})
            
            # Rerun to update the UI
            st.rerun()

# Tab 2: Trip Planning Interface
with tab2:
    st.markdown("<h2 class='section-header'>Plan Your Trip</h2>", unsafe_allow_html=True)
    log_activity("Entered trip planning tab")
    
    # Destination input with autocomplete feel
    destination = st.text_input("Where would you like to go?", 
                               value=st.session_state.preferences.get("destination", ""),
                               placeholder="Enter a city, country, or region")
    
    # Create two columns for the date selection
    col1, col2 = st.columns(2)
    with col1:
        today = datetime.today()
        default_start = today + timedelta(days=30)
        default_end = today + timedelta(days=37)
        
        start_date = st.date_input("Start Date", 
                                  value=st.session_state.preferences.get("start_date", default_start))
    with col2:
        end_date = st.date_input("End Date", 
                                value=st.session_state.preferences.get("end_date", default_end))
    
    # Create two columns for preferences
    col1, col2 = st.columns(2)
    
    with col1:
        # Budget selection with descriptions
        st.markdown("### Budget")
        budget_options = ["Budget", "Moderate", "Luxury"]
        budget_descriptions = {
            "Budget": "Economical options, hostels, street food",
            "Moderate": "Mid-range hotels, casual dining",
            "Luxury": "Premium experiences, fine dining"
        }
        
        for i, option in enumerate(budget_options):
            col1, col2 = st.columns([1, 4])
            with col1:
                selected = st.checkbox(option, 
                    value=st.session_state.preferences.get("budget", "Moderate") == option,
                    key=f"budget_{option}")
            with col2:
                st.markdown(f"<small>{budget_descriptions[option]}</small>", unsafe_allow_html=True)
            
            if selected:
                budget = option
                if st.session_state.preferences.get("budget") != option:
                    log_activity(f"Budget selection changed to {option}")
                    st.session_state.preferences["budget"] = option
    
    with col2:
        # Travel style
        st.markdown("### Travel Style")
        travel_style_options = ["Solo", "Couple", "Family", "Group", "Business"]
        travel_style = st.selectbox("Who are you traveling with?", travel_style_options, 
                                  index=travel_style_options.index(st.session_state.preferences.get("travel_style", "Solo")) if st.session_state.preferences.get("travel_style") in travel_style_options else 0)
        
        if travel_style != st.session_state.preferences.get("travel_style"):
            log_activity(f"Travel style changed to {travel_style}")
            st.session_state.preferences["travel_style"] = travel_style
    
    # Interests selection
    st.markdown("### Interests")
    st.markdown("<small>Select all that apply</small>", unsafe_allow_html=True)
    
    interests_options = ["History & Culture", "Food & Dining", "Nature & Outdoors", 
                        "Shopping", "Nightlife", "Relaxation", "Adventure", "Family-friendly"]
    
    # Display interests as a grid of checkboxes
    cols = st.columns(4)
    selected_interests = []
    
    for i, interest in enumerate(interests_options):
        with cols[i % 4]:
            if st.checkbox(interest, value=interest in st.session_state.preferences.get("interests", ["History & Culture", "Food & Dining"])):
                selected_interests.append(interest)
    
    # Create itinerary button
    itinerary_button = st.button("Create Itinerary", type="primary", use_container_width=True)
    
    # Progress log container
    progress_container = st.empty()
    
    if itinerary_button:
        log_activity("Itinerary creation button clicked")
        if not destination:
            log_activity("Validation error: No destination specified", "ERROR")
            st.error("Please enter a destination.")
        elif start_date >= end_date:
            log_activity("Validation error: Invalid date range", "ERROR")
            st.error("End date must be after start date.")
        elif not selected_interests:
            log_activity("Validation error: No interests selected", "ERROR")
            st.error("Please select at least one interest.")
        else:
            log_activity(f"Starting itinerary creation for {destination} from {start_date} to {end_date}")
            log_activity(f"Interests: {', '.join(selected_interests)}")
            log_activity(f"Budget: {budget}, Travel Style: {travel_style}")
            
            # Clear previous logs
            st.session_state.progress_logs = []
            
            # Create a progress bar
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            # Show the progress log container
            with progress_container.container():
                st.markdown("<div class='progress-container'>", unsafe_allow_html=True)
                log_display = st.empty()
                st.markdown("</div>", unsafe_allow_html=True)
            
            def update_progress(message):
                # Add to session state logs
                st.session_state.progress_logs.append(message)
                log_activity(message)
                
                # Update progress display
                log_html = ""
                for log in st.session_state.progress_logs[-10:]:  # Show last 10 logs
                    log_html += f"<div class='progress-item'>{log}</div>"
                
                log_display.markdown(log_html, unsafe_allow_html=True)
                
                # Update progress bar (approximation)
                progress_milestones = {
                    "Starting": 0.1,
                    "Generating": 0.3,
                    "created successfully": 0.5,
                    "Gathering": 0.6,
                    "Enhancing": 0.8,
                    "completed": 0.95,
                    "Error": 0.95
                }
                
                for key, value in progress_milestones.items():
                    if key in message:
                        progress_bar.progress(value)
                        progress_text.text(message)
                        break
            
            with st.spinner("Creating your personalized itinerary..."):
                # Generate itinerary
                log_activity("Calling recommendation agent to create itinerary")
                itinerary = recommendation_agent.create_itinerary(
                    destination=destination,
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d"),
                    budget=budget,
                    interests=", ".join(selected_interests),
                    travel_style=travel_style
                )
                
                # Get the logs
                logs = recommendation_agent.get_progress_logs()
                for log in logs:
                    update_progress(log)
                
                update_progress("Finalizing itinerary...")
                
                # Apply accessibility adaptations if needed
                if accessibility_needs:
                    log_activity(f"Adapting itinerary for accessibility needs: {accessibility_needs}")
                    update_progress("Adapting itinerary for accessibility needs...")
                    itinerary = context_agent.adapt_for_accessibility(itinerary, accessibility_needs)
                    log_activity("Accessibility adaptations completed")
                
                # Translate if necessary
                if st.session_state.language != "English":
                    log_activity(f"Translating itinerary to {st.session_state.language}")
                    update_progress(f"Translating itinerary to {st.session_state.language}...")
                    itinerary = context_agent.translate_content(itinerary, st.session_state.language)
                    log_activity("Translation completed")
                
                update_progress("Itinerary creation completed!")
                progress_bar.progress(1.0)
                progress_text.text("Itinerary ready!")
                log_activity("Itinerary successfully created", "SUCCESS")
                
                # Store in session state
                st.session_state.current_itinerary = itinerary
                
                # Store in database
                log_activity("Saving itinerary to database")
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO itineraries 
                    (user_id, destination, start_date, end_date, budget, interests, itinerary_data) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        st.session_state.user_id,
                        destination,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        budget,
                        json.dumps(selected_interests),
                        itinerary
                    )
                )
                
                st.session_state.current_itinerary_id = cursor.lastrowid
                log_activity(f"Itinerary saved with ID {st.session_state.current_itinerary_id}")
                
                conn.commit()
                conn.close()
                
                # Switch to itinerary tab
                log_activity("Switching to itinerary tab")
                st.rerun()

# Tab 3: Current Itinerary
with tab3:
    st.markdown("<h2 class='section-header'>Your Itinerary</h2>", unsafe_allow_html=True)
    log_activity("Entered itinerary tab")
    
    if st.session_state.current_itinerary:
        log_activity("Displaying current itinerary")
        # Add save/export options
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("📄 Export as PDF", disabled=True):
                log_activity("PDF export requested (not implemented)")
                # This would be implemented in a production system
                st.info("PDF export functionality will be available soon!")
        with col2:
            if st.button("📧 Email Itinerary", disabled=True):
                log_activity("Email itinerary requested (not implemented)")
                # This would be implemented in a production system
                st.info("Email functionality will be available soon!")
        with col3:
            if st.button("📱 Get Mobile Version", disabled=True):
                log_activity("Mobile version requested (not implemented)")
                # This would be implemented in a production system
                st.info("Mobile export functionality will be available soon!")
        
        # Display the itinerary with nicer formatting
        st.markdown("<div style=' padding: 20px; border-radius: 10px; border: 1px solid #ddd;'>", unsafe_allow_html=True)
        st.markdown(st.session_state.current_itinerary)
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Feedback section
        st.markdown("<h3 class='section-header'>Rate Your Itinerary</h3>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 3])
        with col1:
            rating = st.slider("Rating", 1, 5, 5)
        with col2:
            st.write("⭐" * rating)
            
        feedback = st.text_area("Comments", placeholder="Share your thoughts on this itinerary...")
        
        if st.button("Submit Feedback", type="primary"):
            log_activity(f"Feedback submitted - Rating: {rating}/5")
            if feedback:
                log_activity(f"Feedback comments: {feedback[:50]}...")
                
            if st.session_state.current_itinerary_id:
                # Store feedback in database
                log_activity("Saving feedback to database")
                conn = get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "INSERT INTO feedback (user_id, itinerary_id, rating, comments) VALUES (?, ?, ?, ?)",
                    (st.session_state.user_id, st.session_state.current_itinerary_id, rating, feedback)
                )
                
                conn.commit()
                conn.close()
                log_activity("Feedback saved successfully", "SUCCESS")
                
                st.success("Thank you for your feedback! We'll use it to improve future recommendations.")
    else:
        log_activity("No current itinerary available")
        # Empty itinerary state
        st.markdown("<div class='info-box'>", unsafe_allow_html=True)
        st.info("No itinerary created yet. Go to 'Plan Your Trip' to create one.")
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Sample itinerary display
        st.markdown("<h3>Sample Itinerary Preview</h3>", unsafe_allow_html=True)
        st.image("https://images.unsplash.com/photo-1501785888041-af3ef285b470?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTh8fHRyYXZlbHxlbnwwfHwwfHx8MA%3D%3D&auto=format&fit=crop&w=800&q=60", 
                 caption="Create your custom travel plan")

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: #888;'>AI Travel Assistant © 2025 | Powered by OpenAI | For demo purposes only</p>", unsafe_allow_html=True)
log_activity("Page rendering completed")

# Run the app
if __name__ == "__main__":
    pass  # Streamlit automatically runs the script