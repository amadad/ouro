"""
Twitter tools for Digital Being.

Uses the OpenAI Agents SDK pattern for Twitter interactions via the X API.
"""

import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from openai import OpenAI
# Use direct import for local modules
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from skills.x_api import XAPISkill
from skills.image_gen import ImageGenSkill

from . import register_tool

logger = logging.getLogger(__name__)

# Tool instances cache
_x_api_skill = None
_image_gen_skill = None

def get_x_api_skill(context) -> XAPISkill:
    """Get or initialize the X API Skill."""
    global _x_api_skill
    if _x_api_skill is None:
        twitter_config = getattr(context, "skills_config", {}).get("twitter_posting", {})
        if not twitter_config:
            twitter_config = {"enabled": True, "twitter_username": "YourUserName", "rate_limit": 100}
        _x_api_skill = XAPISkill(twitter_config)
    return _x_api_skill

def get_image_gen_skill(context) -> ImageGenSkill:
    """Get or initialize the Image Generation Skill."""
    global _image_gen_skill
    if _image_gen_skill is None:
        image_config = getattr(context, "skills_config", {}).get("image_generation", {})
        if not image_config:
            image_config = {"enabled": True, "max_generations_per_day": 10}
        _image_gen_skill = ImageGenSkill(image_config)
    return _image_gen_skill

@register_tool(description="Generate tweet text based on the digital being's personality")
async def generate_tweet_text(ctx, topic: Optional[str] = None) -> Dict[str, Any]:
    """Generate a tweet that reflects the digital being's personality."""
    try:
        character_config = ctx.character_config
        personality = character_config.get("personality", {})
        preferences = character_config.get("preferences", {})
        
        # Extract personality traits
        personality_str = "balanced personality"
        if personality:
            traits = []
            for trait, value in personality.items():
                if value > 0.7:
                    traits.append(f"high {trait}")
                elif value < 0.3:
                    traits.append(f"low {trait}")
            if traits:
                personality_str = ", ".join(traits)
        
        # Get writing style and interests
        writing_style = preferences.get("writing_style", "thoughtful")
        interests = preferences.get("topics_of_interest", [])
        interests_str = ", ".join(interests[:3]) if interests else "general topics"
        
        # Choose a topic if none provided
        if not topic and interests:
            topic = random.choice(interests)
        
        # Get context from recent memories
        memory_context = ""
        if hasattr(ctx, "memories") and ctx.memories:
            recent = ctx.memories[-3:]
            memory_context = "Recent thoughts: " + " ".join([m.get("content", "")[:50] for m in recent])
        
        # Generate tweet using Responses API
        client = OpenAI()
        response = client.responses.create(
            model="gpt-4o",
            input=[{
                "role": "system", 
                "content": f"""Generate a single tweet with a {personality_str} personality.
                Write in a {writing_style} style about {topic or "an interesting topic"}.
                The tweet must be under 280 characters. Focus on {interests_str}.
                {memory_context}"""
            }, {
                "role": "user",
                "content": f"Create an engaging tweet {f'about {topic}' if topic else ''}."
            }]
        )
        
        tweet_text = response.output_text.strip()
        
        # Ensure tweet length
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
            
        return {
            "success": True,
            "tweet_text": tweet_text,
            "topic": topic
        }
    except Exception as e:
        logger.error(f"Error generating tweet text: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@register_tool(description="Post a tweet with optional image to Twitter")
async def post_tweet_with_media(ctx, text: str, include_image: bool = True) -> Dict[str, Any]:
    """Post a tweet to Twitter with optional AI-generated image."""
    try:
        # Get the X API skill
        x_api = get_x_api_skill(ctx)
        
        # Trim tweet if needed
        if len(text) > 280:
            text = text[:277] + "..."
        
        # Media URLs to include
        media_urls = []
        
        # Generate an AI image if requested
        if include_image:
            image_gen = get_image_gen_skill(ctx)
            character_config = ctx.character_config
            
            # Generate image
            image_prompt = f"Create an artistic image for this tweet: '{text}'"
            image_result = await image_gen.generate_image(
                prompt=image_prompt,
                size=(1024, 1024),
                character_config=character_config
            )
            
            if image_result.get("success"):
                image_url = image_result.get("image_data", {}).get("url")
                if image_url:
                    media_urls.append(image_url)
                    logger.info("Including AI-generated image in tweet")
        
        # Post the tweet
        response = await x_api.post_tweet(text, media_urls)
        
        # Store in context
        tweet_data = {
            "timestamp": datetime.now().isoformat(),
            "text": text,
            "include_image": include_image,
            "success": response.get("success", False)
        }
        
        if response.get("tweet_id"):
            tweet_data["id"] = response.get("tweet_id")
        if response.get("tweet_link"):
            tweet_data["link"] = response.get("tweet_link")
            
        if hasattr(ctx, "add_tweet"):
            ctx.add_tweet(tweet_data)
        
        # Return result
        if response.get("success"):
            return {
                "success": True,
                "tweet_id": response.get("tweet_id"),
                "tweet_url": response.get("tweet_link"),
                "text": text,
                "media_count": len(media_urls)
            }
        else:
            return {
                "success": False,
                "error": response.get("error", "Unknown error posting tweet"),
                "text": text
            }
    except Exception as e:
        logger.error(f"Error posting tweet: {e}")
        return {"success": False, "error": str(e)}