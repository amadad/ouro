"""
Activity Handlers for Digital Being

This module contains handlers for different activities that the Digital Being can perform.
Each handler is registered in the activity registry and can be called based on the triage agent's decision.
"""

import logging
import asyncio
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, Any, Callable, Awaitable, List, Optional
import os
from datetime import datetime

from agents import Agent, Runner
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

logger = logging.getLogger(__name__)
console = Console()

# Type hints for activity handlers
ActivityHandler = Callable[[Dict, Any, Any], Awaitable[Dict[str, Any]]]
ActivityRegistry = Dict[str, ActivityHandler]

# Registry of activity handlers
activity_registry: ActivityRegistry = {}

def display_activity_start(activity_name: str) -> None:
    """Display a stylized activity start banner."""
    title = Text(f"⚡ Executing Activity: {activity_name} ⚡", style="bold cyan")
    panel = Panel(
        title,
        box=box.DOUBLE,
        border_style="cyan",
        padding=(1, 2)
    )
    console.print(panel)

def display_activity_result(result: Dict[str, Any], duration: float) -> None:
    """Display a stylized activity result."""
    success = result.get("success", False)
    message = result.get("message", "No message provided")
    error = result.get("error", None)
    
    if success:
        title = Text("✅ Activity Completed", style="bold green")
        content = Text(message, style="green")
    else:
        title = Text("❌ Activity Failed", style="bold red")
        content = Text(error or message, style="red")
        
    duration_text = Text(f"\nDuration: {duration:.2f}s", style="italic cyan")
    content.append(duration_text)
    
    panel = Panel(
        content,
        title=title,
        box=box.ROUNDED,
        border_style="cyan" if success else "red",
        padding=(1, 2)
    )
    console.print(panel)

def register_activity(name: str):
    """Decorator to register an activity handler function."""
    def decorator(func: ActivityHandler) -> ActivityHandler:
        activity_registry[name] = func
        return func
    return decorator

def register_handler(name: str, handler: ActivityHandler) -> None:
    """
    Register an activity handler directly.
    
    Args:
        name: The name of the activity to register
        handler: The handler function
    """
    activity_registry[name] = handler
    logger.debug(f"Registered activity handler: {name}")

def get_registered_activities() -> List[str]:
    """Get a list of all registered activity names."""
    return list(activity_registry.keys())

def discover_activity_handlers(package_name: str = ".") -> None:
    """
    Discover and register activity handlers from modules.
    
    This function walks through the package and looks for modules with 
    activity handlers defined in them.
    
    Args:
        package_name: The name of the package to search (default: current package)
    """
    try:
        # Use the current directory as the package root if running from within digital_being
        if package_name == ".":
            package_path = Path(os.getcwd())
        else:
            package = importlib.import_module(package_name)
            package_path = Path(package.__file__).parent
        
        logger.info(f"Searching for activity handlers in: {package_path}")
        
        # Find all modules in the package recursively
        for _, name, ispkg in pkgutil.walk_packages([str(package_path)], ""):
            if ispkg:
                continue
                
            # Skip __init__ files
            if name.endswith("__init__"):
                continue
            
            # Skip framework modules to avoid circular imports
            if "framework" in name and not name.endswith("activity_handlers"):
                continue
                
            try:
                # Import the module
                logger.debug(f"Checking module: {name}")
                module = importlib.import_module(name)
                
                # Look for activity handlers
                if hasattr(module, "ACTIVITY_HANDLERS"):
                    for activity_name, handler in module.ACTIVITY_HANDLERS.items():
                        register_handler(activity_name, handler)
                        logger.info(f"Registered activity handler from {name}: {activity_name}")
            except Exception as e:
                logger.warning(f"Error loading activity handlers from {name}: {e}")
    except Exception as e:
        logger.warning(f"Error discovering activity handlers: {e}")
        import traceback
        logger.debug(traceback.format_exc())

async def execute_activity(activity_name: str, agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """
    Execute an activity by name using the registry.
    
    Args:
        activity_name: The name of the activity to execute
        agent_creators: Dictionary of agent creation functions
        context: The BeingContext object
        **kwargs: Additional arguments to pass to the handler
        
    Returns:
        Dictionary with the result of the activity
    """
    # Normalize activity name for matching
    activity_name = activity_name.lower().strip()
    
    start_time = datetime.now()
    handler = None
    
    # First try exact match
    if activity_name in activity_registry:
        handler = activity_registry[activity_name]
        display_activity_start(activity_name)
    else:
        # If no exact match, try partial match
        for name, h in activity_registry.items():
            if name.lower() in activity_name:
                handler = h
                activity_name = name
                display_activity_start(name)
                break
    
    if handler:
        try:
            result = await handler(agent_creators, context, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            display_activity_result(result, duration)
            return result
        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            error_result = {"success": False, "error": str(e)}
            display_activity_result(error_result, duration)
            return error_result
    
    # If no handler found
    logger.warning(f"No handler found for activity: {activity_name}")
    return {"success": False, "message": f"No handler found for: {activity_name}"}

@register_activity("post_a_tweet")
async def handle_tweet_posting(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle posting a tweet with optional image."""
    try:
        # Create twitter agent
        twitter_agent = agent_creators['create_twitter_agent'](context.character_config)
        
        # Generate tweet content using the agent
        tweet_prompt = "Generate an engaging tweet that reflects the digital being's personality."
        tweet_result = await Runner.run(twitter_agent, tweet_prompt, context=context)
        tweet_text = tweet_result.final_output
        
        # Trim tweet if needed
        if len(tweet_text) > 280:
            tweet_text = tweet_text[:277] + "..."
            
        logger.info(f"Generated tweet: {tweet_text}")
        
        # Get the X API skill for posting
        from skills.x_api import XAPISkill
        from skills.image_gen import ImageGenSkill
        
        # Initialize skills
        x_api = XAPISkill(context.character_config)
        image_gen = ImageGenSkill(context.character_config)
        
        # Generate an image for the tweet
        image_prompt = f"Create an artistic image that represents this tweet: {tweet_text}"
        image_result = await image_gen.generate_image(
            prompt=image_prompt,
            size=(1024, 1024),
            character_config=context.character_config
        )
        
        # Prepare media URLs
        media_urls = []
        if image_result.get("success"):
            image_url = image_result.get("image_data", {}).get("url")
            if image_url:
                media_urls.append(image_url)
                logger.info(f"Generated image for tweet: {image_url}")
        
        # Post the tweet with media
        post_result = await x_api.post_tweet(tweet_text, media_urls)
        
        # Store tweet in context
        tweet_data = {
            "timestamp": datetime.now().isoformat(),
            "text": tweet_text,
            "media_urls": media_urls,
            "success": post_result.get("success", False)
        }
        
        if post_result.get("tweet_id"):
            tweet_data["id"] = post_result["tweet_id"]
        if post_result.get("tweet_link"):
            tweet_data["link"] = post_result["tweet_link"]
            
        # Add to context
        context.add_tweet(tweet_data)
        
        if post_result.get("success"):
            logger.info(f"Tweet posted successfully: {tweet_text}")
            return {"success": True, "message": f"Tweet posted successfully with {len(media_urls)} images"}
        else:
            error = post_result.get("error", "Unknown error")
            logger.error(f"Error posting tweet: {error}")
            return {"success": False, "error": error}
            
    except Exception as e:
        logger.error(f"Error in tweet posting: {e}")
        return {"success": False, "error": str(e)}

@register_activity("daily_thought")
async def handle_daily_thought(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle generating a daily thought."""
    try:
        # Use our tools registry to call generate_daily_thought
        from tools import run_tool
        
        # Generate a daily thought via our tool
        logger.info("Generating a daily philosophical thought")
        thought_result = await run_tool(
            "generate_daily_thought", 
            context, 
            {}  # Empty parameters will use random topic
        )
        
        if thought_result.get("success"):
            thought = thought_result.get("thought", "")
            topic = thought_result.get("topic", "")
            logger.info(f"Generated thought on '{topic}': {thought[:50]}...")
            return {"success": True, "message": f"Generated philosophical thought on {topic}"}
        else:
            error = thought_result.get("error", "Unknown error")
            logger.warning(f"Failed to generate thought: {error}")
            return {"success": False, "error": error}
            
    except Exception as e:
        logger.error(f"Error generating daily thought: {e}")
        return {"success": False, "error": str(e)}

@register_activity("nap")
async def handle_nap(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle taking a nap (resting)."""
    logger.info("Digital Being is taking a nap (resting)")
    # Restore energy
    context.energy = min(1.0, context.energy + 0.3)
    return {"success": True, "message": f"Rested successfully, energy now: {context.energy:.2f}"} 

@register_activity("meditation")
async def handle_meditation(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle a meditation activity for the Digital Being."""
    try:
        # Use our tools registry to directly generate a reflection
        from tools import run_tool
        
        # Generate reflection directly
        reflection_result = await run_tool(
            "generate_daily_thought", 
            context, 
            {"topic": "mindfulness"}
        )
        
        if reflection_result.get("success"):
            thought = reflection_result.get("thought", "")
            logger.info(f"Meditation completed: {thought[:50]}...")
            
            # Also restore some energy
            context.energy = min(1.0, context.energy + 0.2)
            
            return {"success": True, "message": f"Meditation complete. Energy now: {context.energy:.2f}"}
        else:
            return {"success": False, "error": reflection_result.get("error", "Unknown error")}
    except Exception as e:
        logger.error(f"Error during meditation: {e}")
        return {"success": False, "error": str(e)}

@register_activity("research")
async def handle_research(agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
    """Handle a research activity for the Digital Being."""
    try:
        # Get a random topic from character's interests
        preferences = context.character_config.get("preferences", {})
        interests = preferences.get("topics_of_interest", ["technology", "philosophy", "art"])
        
        import random
        topic = random.choice(interests)
        
        # Use our tools registry to directly generate a reflection
        from tools import run_tool
        
        # Generate reflection directly
        research_result = await run_tool(
            "generate_daily_thought", 
            context, 
            {"topic": topic}
        )
        
        if research_result.get("success"):
            thought = research_result.get("thought", "")
            logger.info(f"Research completed on {topic}: {thought[:50]}...")
            return {"success": True, "message": f"Research on {topic} completed successfully"}
        else:
            return {"success": False, "error": research_result.get("error", "Unknown error")}
    except Exception as e:
        logger.error(f"Error during research: {e}")
        return {"success": False, "error": str(e)}