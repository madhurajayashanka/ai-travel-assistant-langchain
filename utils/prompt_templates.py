from langchain.prompts import PromptTemplate

# System prompt for the travel assistant
TRAVEL_ASSISTANT_SYSTEM_PROMPT = """
You are a sophisticated AI travel assistant that helps users plan their trips.
Your goal is to create personalized travel experiences based on user preferences.
Always consider the user's budget, travel dates, interests, and travel style.
Be concise but informative. Focus on providing practical, actionable travel recommendations.
For each recommendation, include a brief description of why it might appeal to the user.
"""

# Template for generating an initial itinerary
ITINERARY_CREATION_TEMPLATE = PromptTemplate(
    input_variables=["destination", "start_date", "end_date", "budget", "interests", "travel_style"],
    template="""
Create a detailed daily itinerary for a trip to {destination} from {start_date} to {end_date}.
Budget level: {budget}
Interests: {interests}
Travel style: {travel_style}

The itinerary should include:
1. Daily activities and attractions that match the user's interests
2. Suggested dining options for each day (breakfast, lunch, dinner)
3. Estimated costs for major activities and meals
4. Transportation recommendations between locations
5. Time estimates for each activity
6. Brief descriptions of why each recommendation fits the user's preferences

Format the itinerary by day, with a clear schedule and all relevant details.
"""
)

# Template for refining recommendations based on context
CONTEXT_AWARE_TEMPLATE = PromptTemplate(
    input_variables=["itinerary", "current_location", "weather", "local_events", "time_of_day"],
    template="""
Given the following itinerary:
{itinerary}

And the current context:
- Current location: {current_location}
- Weather conditions: {weather}
- Local events happening now: {local_events}
- Time of day: {time_of_day}

Please provide updated recommendations or adjustments to the itinerary that take into account this real-time information.
Focus on practical advice given the current circumstances.
"""
)

# Template for processing user feedback
FEEDBACK_PROCESSING_TEMPLATE = PromptTemplate(
    input_variables=["itinerary", "feedback", "rating"],
    template="""
The user has provided the following feedback on this itinerary:
{itinerary}

User rating: {rating}/5
User feedback: {feedback}

Based on this feedback, please suggest specific improvements to the itinerary.
Identify what aspects were liked and disliked, and how the recommendations could better match the user's preferences.
"""
)

# Template for multi-lingual support
TRANSLATION_TEMPLATE = PromptTemplate(
    input_variables=["content", "target_language"],
    template="""
Translate the following travel information into {target_language}:

{content}

Ensure that any specific place names, attraction names, or cultural terms are preserved appropriately.
If certain terms are better left untranslated, keep them in their original form.
"""
)

# Template for accessibility considerations
ACCESSIBILITY_TEMPLATE = PromptTemplate(
    input_variables=["itinerary", "accessibility_needs"],
    template="""
Review the following travel itinerary:
{itinerary}

The user has the following accessibility requirements:
{accessibility_needs}

Please modify the itinerary to accommodate these accessibility needs.
For each recommendation, note:
1. Whether it's accessible given the user's requirements
2. Any specific accessibility features or challenges
3. Alternative options if a recommended place isn't suitable
"""
)

# Template for cost optimization
BUDGET_OPTIMIZATION_TEMPLATE = PromptTemplate(
    input_variables=["itinerary", "strict_budget"],
    template="""
Review the following travel itinerary:
{itinerary}

The user has indicated a stricter budget constraint of: {strict_budget}

Please optimize this itinerary to reduce costs while maintaining the best possible experience:
1. Suggest more affordable alternatives to expensive activities
2. Recommend budget-friendly dining options
3. Optimize transportation costs
4. Identify free or low-cost attractions that still match the user's interests
5. Provide specific money-saving tips relevant to the destination
"""
)