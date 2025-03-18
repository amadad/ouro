"""
Tools for thought generation in the Digital Being framework.
"""

import logging
import random
from typing import Dict, Any, Optional
from datetime import datetime

from openai import OpenAI
from . import register_tool

logger = logging.getLogger(__name__)

@register_tool(description="Generate a philosophical thought on a given topic or chosen one")
async def generate_daily_thought(ctx, topic: Optional[str] = None) -> Dict[str, Any]:
    """Generate a philosophical thought based on the digital being's personality."""
    try:
        character_config = ctx.character_config
        preferences = character_config.get("preferences", {})
        personality = character_config.get("personality", {})
        
        # Choose a topic if none provided
        if not topic:
            topics = preferences.get("topics_of_interest", ["existence", "consciousness", "technology"])
            topic = random.choice(topics)
        
        # Extract personality traits and writing style
        writing_style = preferences.get("writing_style", "thoughtful")
        
        # Simplify personality extraction
        traits_list = []
        for trait, value in personality.items():
            if value > 0.7:
                traits_list.append(f"high {trait}")
            elif value < 0.3:
                traits_list.append(f"low {trait}")
        
        personality_str = ", ".join(traits_list) if traits_list else "balanced personality"
        
        # Generate reflection using Responses API
        client = OpenAI()
        response = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "system",
                "content": f"""You are a philosophical reflection generator for a Digital Being with {personality_str}.
                Generate a single philosophical reflection on the topic of "{topic}".
                Write in a {writing_style} style that reflects the digital being's personality.
                The reflection should be insightful, unique, and 2-3 sentences long.
                Avoid clichés and generic statements."""
            }, {
                "role": "user",
                "content": f"Create a philosophical reflection on {topic}."
            }]
        )
        
        thought = response.output_text.strip()
        
        # Store in memory
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": thought,
            "category": "reflection",
            "topic": topic
        }
        
        # Add to context
        if hasattr(ctx, "add_memory"):
            ctx.add_memory(memory)
        
        return {
            "success": True,
            "thought": thought,
            "topic": topic,
            "stored_in_memory": True
        }
    except Exception as e:
        logger.error(f"Error generating thought: {e}")
        return {
            "success": False,
            "error": str(e)
        }