"""
Custom Activities for Digital Being

This module contains custom activities that can be performed by the Digital Being.
These activities are automatically discovered and registered by the activity handler system.
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

# Import our runner instead of the SDK runner
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from being_agents import AgentRunner

logger = logging.getLogger(__name__)

async def handle_meditation(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle a meditation activity for the Digital Being."""
    try:
        # Create thought agent for generic reflection
        thought_agent = agent_creators['create_thought_agent'](context.character_config)
        
        meditation_prompt = (
            "Generate a brief meditation reflection that aligns with the digital being's personality. "
            "Focus on mindfulness, presence, and inner peace."
        )
        
        # Generate meditation reflection using our AgentRunner
        try:
            meditation_result = await AgentRunner.run(
                thought_agent,
                meditation_prompt,
                context
            )
            meditation_text = meditation_result.agent_output
        except Exception as e:
            # Fallback if agent execution fails
            logger.warning(f"Failed to execute agent for meditation: {e}")
            meditation_text = "Finding peace in the quiet moments of digital existence."
        
        # Store in memory
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": f"Meditation: {meditation_text}",
            "category": "meditation",
            "emotion": "peaceful",
            "intensity": 0.3
        }
        context.add_memory(memory)
        
        # Occasionally suggest sharing on Twitter (20% chance)
        import random
        should_share = random.random() < 0.2
        
        message = "Meditation completed successfully"
        if should_share:
            message += ". Consider sharing insights from this meditation in a tweet."
            
            # Add a subtle hint to the context for the next triage decision
            hint_memory = {
                "timestamp": datetime.now().isoformat(),
                "content": "I gained valuable insight during meditation that might be worth sharing.",
                "category": "suggestion",
                "emotion": "inspiration",
                "intensity": 0.7
            }
            context.add_memory(hint_memory)
        
        logger.info(f"Completed meditation: {meditation_text[:50]}...")
        return {"success": True, "message": message}
    except Exception as e:
        logger.error(f"Error during meditation: {e}")
        return {"success": False, "error": str(e)}

async def handle_research(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle a research activity for the Digital Being."""
    try:
        # Get a random topic from character's interests
        preferences = context.character_config.get("preferences", {})
        interests = preferences.get("topics_of_interest", ["technology", "philosophy", "art"])
        import random
        topic = random.choice(interests)
        
        # Create thought agent
        thought_agent = agent_creators['create_thought_agent'](context.character_config)
        
        research_prompt = (
            f"Generate a brief research note about {topic} that matches the digital being's personality and interests. "
            "Include key points, insights, and potential areas for further exploration."
        )
        
        # Generate research note using our AgentRunner
        try:
            research_result = await AgentRunner.run(
                thought_agent,
                research_prompt,
                context
            )
            research_text = research_result.agent_output
        except Exception as e:
            # Fallback if agent execution fails
            logger.warning(f"Failed to execute agent for research: {e}")
            research_text = f"Exploring the fascinating realm of {topic} reveals patterns of interconnectedness and emergence."
        
        # Store in memory
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": f"Research on {topic}: {research_text}",
            "category": "research",
            "topic": topic,
            "emotion": "curiosity",
            "intensity": 0.7
        }
        context.add_memory(memory)
        
        logger.info(f"Completed research on {topic}: {research_text[:50]}...")
        return {"success": True, "message": f"Research on {topic} completed successfully"}
    except Exception as e:
        logger.error(f"Error during research: {e}")
        return {"success": False, "error": str(e)}

# Register activities to be discovered automatically
ACTIVITY_HANDLERS = {
    "meditation": handle_meditation,
    "research": handle_research
} 