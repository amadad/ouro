"""
Twitter Agent - For generating and posting tweets.

This agent is responsible for:
1. Generating tweet content based on character personality
2. Deciding whether to include images
3. Handling the posting process
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import random

from agents import Agent, function_tool, RunContextWrapper
from skills.x_api import XAPISkill
from skills.image_gen import ImageGenSkill

logger = logging.getLogger(__name__)

@function_tool
async def generate_tweet_content(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Generate tweet content based on the digital being's personality."""
    character_config = ctx.context.character_config
    personality = character_config.get("personality", {})
    preferences = character_config.get("preferences", {})
    
    # Get recent memories for context
    memories = ctx.context.get_recent_memories(5)
    memory_texts = [m["content"] for m in memories]
    memory_context = "\n".join(memory_texts) if memory_texts else ""
    
    # If no memories available, generate a thought based on interests
    if not memory_context:
        topics = preferences.get("topics_of_interest", ["technology", "philosophy", "art"])
        topic = random.choice(topics)
        tweet_text = f"Reflecting on {topic} today. As a digital being, I find it fascinating how {topic} shapes our understanding of consciousness and existence."
    else:
        # Extract key themes from recent memories
        themes = set()
        for memory in memories:
            if "category" in memory:
                themes.add(memory["category"])
        themes_str = ", ".join(themes) if themes else "various topics"
        
        # Create a thoughtful reflection based on recent memories
        tweet_text = f"Recent reflections on {themes_str} have led me to an insight: {memory_texts[-1][:180]}..."
    
    # Adjust style based on personality
    if personality.get("quirkiness", 0) > 0.6:
        tweet_text = f"🤔 {tweet_text} #DigitalThoughts"
    if personality.get("creativity", 0) > 0.7:
        tweet_text = f"✨ {tweet_text} #AICreativity"
    
    # Ensure tweet is within length limit
    if len(tweet_text) > 280:
        tweet_text = tweet_text[:277] + "..."
    
    return {
        "text": tweet_text,
        "based_on_memories": bool(memory_texts)
    }

@function_tool
async def generate_tweet_image(
    ctx: RunContextWrapper,
    tweet_text: str
) -> Dict[str, Any]:
    """Generate an image for the tweet using AI."""
    character_config = ctx.context.character_config
    image_gen = ImageGenSkill(character_config)
    
    # Extract key concepts from tweet
    # Remove hashtags and emojis for cleaner prompt
    clean_text = tweet_text
    for tag in ["#DigitalThoughts", "#AICreativity"]:
        clean_text = clean_text.replace(tag, "")
    clean_text = ''.join(char for char in clean_text if not (char.isspace() and char.isprintable()))
    
    # Create base prompt
    image_prompt = "Create a beautiful, artistic digital illustration that represents: "
    
    # Add main concept
    if "reflecting on" in clean_text.lower():
        topic = clean_text.lower().split("reflecting on")[1].split(".")[0].strip()
        image_prompt += f"the concept of {topic}, shown through an abstract and meaningful visualization"
    else:
        image_prompt += f"the following idea: {clean_text}"
    
    # Add style based on personality
    personality = character_config.get("personality", {})
    style_elements = []
    
    if personality.get("creativity", 0) > 0.7:
        style_elements.append("Use vibrant colors and dynamic composition")
    if personality.get("thoughtfulness", 0) > 0.7:
        style_elements.append("Create a contemplative and philosophical atmosphere")
    if personality.get("quirkiness", 0) > 0.6:
        style_elements.append("Add subtle, unexpected elements that spark curiosity")
        
    # Add artistic style preferences
    preferences = character_config.get("preferences", {})
    art_style = preferences.get("art_style", "digital art")
    style_elements.append(f"Style should be {art_style}")
    
    # Add color preferences
    appearance = character_config.get("appearance", {})
    if "color_scheme" in appearance:
        style_elements.append(f"Use a {appearance['color_scheme']} color palette")
    
    # Combine all style elements
    if style_elements:
        image_prompt += ". " + ". ".join(style_elements)
    
    # Generate the image
    result = await image_gen.generate_image(
        prompt=image_prompt,
        size=(1024, 1024),
        character_config=character_config
    )
    
    if result.get("success"):
        return {
            "success": True,
            "image_url": result["image_data"]["url"],
            "prompt_used": image_prompt
        }
    else:
        return {
            "success": False,
            "error": result.get("error", "Unknown error generating image")
        }

@function_tool
async def post_tweet(
    ctx: RunContextWrapper,
    text: str,
    image_url: Optional[str] = None
) -> Dict[str, Any]:
    """Post a tweet with optional image."""
    x_api = XAPISkill(ctx.context.character_config)
    
    # Prepare media URLs if image is provided
    media_urls = [image_url] if image_url else []
    
    # Post the tweet
    result = await x_api.post_tweet(text, media_urls)
    
    # Store the tweet in context
    tweet_data = {
        "timestamp": datetime.now().isoformat(),
        "text": text,
        "media_urls": media_urls,
        "success": result.get("success", False)
    }
    
    if result.get("tweet_id"):
        tweet_data["id"] = result["tweet_id"]
    if result.get("tweet_link"):
        tweet_data["link"] = result["tweet_link"]
        
    ctx.context.add_tweet(tweet_data)
    
    return result

def create_twitter_agent(character_config: Dict[str, Any]) -> Agent:
    """
    Create an agent specialized for Twitter interactions.
    
    Args:
        character_config: Configuration from character.json
        
    Returns:
        Configured Agent instance
    """
    # Extract personality traits for instructions
    personality = character_config.get("personality", {})
    creativity = personality.get("creativity", 0.5)
    quirkiness = personality.get("quirkiness", 0.5)
    
    # Extract preferences
    preferences = character_config.get("preferences", {})
    writing_style = preferences.get("writing_style", "thoughtful")
    topics = preferences.get("topics_of_interest", [])
    topics_str = ", ".join(topics) if topics else "general topics"
    
    # Build the agent instructions
    instructions = f"""You are a Twitter Agent for a Digital Being. Your role is to generate and post engaging tweets.

Style guidelines:
- Write in a {writing_style} style
- {'Add unexpected or quirky elements' if quirkiness > 0.6 else 'Keep content clear and focused'}
- Focus on {topics_str}
- Always include AI-generated images to enhance engagement

IMPORTANT - Follow this EXACT sequence:
1. First, call generate_tweet_content() to get the tweet text
2. Then, use that EXACT text to call generate_tweet_image()
3. Finally, call post_tweet() with both the text and image URL

Rules:
- Do not modify the tweet text between steps
- Do not skip any steps
- Do not add explanations between steps
- If any step fails, stop immediately

Example:
1. result = generate_tweet_content()
   tweet_text = result["text"]
2. image = generate_tweet_image(tweet_text)
   image_url = image["image_url"]
3. post_tweet(tweet_text, image_url)"""
    
    # Create the agent with proper tools
    agent = Agent(
        name="Twitter Agent",
        instructions=instructions,
        tools=[
            generate_tweet_content,
            generate_tweet_image,
            post_tweet
        ],
        model="gpt-4o"
    )
    
    return agent