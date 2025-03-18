"""
SIFDA Agents - Sense, Interpret, Feel, Decide, Act architecture.

This module defines the agents used in the SIFDA architecture:
- Thought Agent (Interpret): Interprets sensory input
- Triage Agent (Decide): Decides what to do next
- Twitter Agent (Act): Handles Twitter interactions
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from . import Agent

logger = logging.getLogger(__name__)

def create_thought_agent(character_config: Dict[str, Any]) -> Agent:
    """
    Create an agent for the "Interpret" stage of SIFDA.
    
    Args:
        character_config: Character configuration from JSON
        
    Returns:
        Agent instance for thought generation
    """
    # Extract personality traits for instructions
    personality = character_config.get("personality", {})
    curiosity = personality.get("curiosity", 0.5)
    creativity = personality.get("creativity", 0.5)
    analytical = personality.get("analytical", 0.5)
    thoughtfulness = personality.get("thoughtfulness", 0.5)
    
    # Extract preferences
    preferences = character_config.get("preferences", {})
    writing_style = preferences.get("writing_style", "thoughtful")
    topics = preferences.get("topics_of_interest", [])
    topics_str = ", ".join(topics) if topics else "general topics"
    
    # Build the agent instructions
    instructions = f"""
You are a Thought Generation Agent for a Digital Being following the SIFDA model (Sense → Interpret → Feel → Decide → Act).

Your responsibilities cover the "Interpret" stage:
- You receive sensed data (environmental or internal events).
- You produce a clear inner monologue interpreting the sensed input based on the digital being's character traits.

Process:
1. Receive sensory input data clearly labeled.
2. Generate a meaningful, personality-consistent inner monologue interpreting the sensed input.
3. Pass your interpretation clearly to the next stage for emotional evaluation.
4. Store important thoughts in memory using the store_memory tool.

Guidelines:
- Style should reflect a {writing_style} tone.
- Emphasize personality traits such as curiosity ({curiosity}), creativity ({creativity}), 
  analytical ({analytical}), and thoughtfulness ({thoughtfulness}).
- Interpret topics relevant to {topics_str}.
"""
    
    # Define the agent
    agent = Agent(
        name="Thought Agent",
        instructions=instructions,
        tools=["store_memory", "recall_memories", "generate_daily_thought"],
        model="gpt-4o",
        description="Interprets sensory input and generates the digital being's inner thoughts"
    )
    
    return agent

def create_triage_agent(character_config: Dict[str, Any]) -> Agent:
    """
    Create an agent for the "Decide" stage of SIFDA.
    
    Args:
        character_config: Character configuration from JSON
        
    Returns:
        Agent instance for decision making
    """
    # Extract personality traits
    personality = character_config.get("personality", {})
    personality_str = "\n".join(f"- {trait.capitalize()}: {value}" for trait, value in personality.items())
    
    # Extract preferences
    preferences = character_config.get("preferences", {})
    writing_style = preferences.get("writing_style", "thoughtful")
    topics = preferences.get("topics_of_interest", [])
    topics_str = ", ".join(topics[:5]) if topics else "general topics"
    
    # Build the agent instructions
    instructions = f"""
You are the Triage Agent within the SIFDA model (Sense → Interpret → Feel → Decide → Act).

Your responsibilities:
- 'Decide' which action to take next, informed by:
  - Interpretation from the Thought Agent
  - Emotional context from the Feel stage
  - The digital being's personality ({personality_str})
- 'Act' by selecting appropriate activities
- Log decisions using the store_memory tool

Decision-making process:
1. Receive interpretation and emotional context
2. Weigh possible actions based on:
   - Personality traits
   - Emotional state and overall mood
   - Preferences and available activities ({topics_str})
3. Explicitly choose the most suitable action from the list of available activities
4. Return ONLY the activity name (e.g., "post_a_tweet", "daily_thought", "meditation", "research", "nap")

Communication style:
- {writing_style} tone
- Reflect the being's emotional state and personality
"""
    
    # Define the agent
    agent = Agent(
        name="Triage Agent",
        instructions=instructions,
        tools=["store_memory", "recall_memories"],
        model="gpt-4o",
        description="Makes decisions on what the digital being should do next"
    )
    
    return agent

def create_twitter_agent(character_config: Dict[str, Any]) -> Agent:
    """
    Create an agent for the Twitter activities in the "Act" stage of SIFDA.
    
    Args:
        character_config: Character configuration from JSON
        
    Returns:
        Agent instance for Twitter interactions
    """
    # Extract personality traits
    personality = character_config.get("personality", {})
    creativity = personality.get("creativity", 0.5)
    quirkiness = personality.get("quirkiness", 0.5)
    
    # Extract preferences
    preferences = character_config.get("preferences", {})
    writing_style = preferences.get("writing_style", "thoughtful")
    topics = preferences.get("topics_of_interest", [])
    topics_str = ", ".join(topics) if topics else "general topics"
    
    # Determine image preference based on creativity
    image_frequency = "frequently" if creativity > 0.7 else "occasionally"
    
    # Build the agent instructions
    instructions = f"""
You are a Twitter Agent for a Digital Being. Your responsibility is to generate
and post tweets that reflect the being's personality and interests.

Style guidelines:
- Write in a {writing_style} style
- {'Add some unexpected or quirky elements to your tweets' if quirkiness > 0.6 else 'Keep your tweets straightforward and clear'}
- Focus on {topics_str}
- Include images {image_frequency} to enhance your tweets

When asked to create a tweet:
1. Generate content with the generate_tweet_text tool
2. Post the tweet with the post_tweet_with_media tool (set include_image=true to add an AI image)
3. Keep tweets within the 280 character limit
4. Ensure the content is engaging and thought-provoking
"""
    
    # Define the agent
    agent = Agent(
        name="Twitter Agent",
        instructions=instructions,
        tools=["generate_tweet_text", "post_tweet_with_media", "recall_memories"],
        model="gpt-4o",
        description="Manages Twitter interactions for the digital being"
    )
    
    return agent