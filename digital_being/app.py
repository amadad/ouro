"""
Digital Being Framework - Using OpenAI Agents SDK

This is a reimplementation of the Digital Being using the OpenAI Agents SDK.
It uses a multi-agent architecture with:
- Triage Agent: Makes decisions about what to do next
- Twitter Agent: Manages Twitter posting
- Thought Agent: Generates philosophical thoughts

The agents are configured from the character.json file, which defines the
personality, preferences, and capabilities of the Digital Being.
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

# Import Agents SDK
from agents import Agent, Runner, trace, set_default_openai_key, set_default_openai_api

# Import our local agent module for dynamic loading
import being_agents

# Import tools module for tool operations
from tools import run_tool

# Import custom logging configuration
from framework.logging_config import configure_logging

# Import activity system
from framework.activity_handlers import discover_activity_handlers
from framework.activity_manager import ActivityManager

# Configure logging with colors
configure_logging(verbose=True)  # Set to True temporarily for debugging
logger = logging.getLogger(__name__)
console = Console()  # For rich output

# Suppress specific loggers for OpenAI and HTTP requests
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("agents").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
# But enable full logging for our activity handlers
logging.getLogger("framework.activity_handlers").setLevel(logging.DEBUG)

# Use BeingContext from schema module
from framework.schema import BeingContext

# Activity costs for energy management
activity_costs = {
    "post_a_tweet": 0.2,
    "daily_thought": 0.2,
    "meditation": 0.1,
    "research": 0.3,
    "nap": -0.4  # Negative cost means it restores energy
}

def display_activity_status(activities: Dict[str, Any], context: Any) -> None:
    """Display current status of all activities with rich styling."""
    console = Console()
    
    # Activity type styling
    activity_styles = {
        "post_a_tweet": "cyan",
        "daily_thought": "yellow",
        "nap": "blue",
        "meditation": "magenta",
        "research": "green"
    }
    
    # Create activity status table
    table = Table(
        title="Activity Status",
        box=box.ROUNDED,
        title_style="bold cyan",
        border_style="cyan",
        padding=(0, 2)
    )
    
    table.add_column("Activity", style="bold")
    table.add_column("Available", justify="center")
    table.add_column("Last Executed", style="italic")
    table.add_column("Cooldown", justify="right", style="dim")
    
    now = datetime.now()
    
    # Convert list to dict if needed
    if isinstance(activities, list):
        # Handle both string lists and dictionary lists
        if activities and isinstance(activities[0], str):
            activities_dict = {name: {"name": name, "available": True, "last_executed": None, "cooldown_remaining": 0} 
                             for name in activities}
        else:
            activities_dict = {activity["name"]: activity for activity in activities}
    else:
        activities_dict = activities
    
    for activity_name, data in activities_dict.items():
        # Get activity-specific color
        color = activity_styles.get(activity_name, "white")
        
        # Format availability
        available = "✅" if data.get("available", True) else "❌"
        
        # Format last executed time
        last_exec = data.get("last_executed")
        if last_exec:
            if isinstance(last_exec, str):
                last_exec = datetime.fromisoformat(last_exec)
            last_exec_str = last_exec.strftime("%H:%M:%S")
        else:
            last_exec_str = "Never"
            
        # Format cooldown
        cooldown = data.get("cooldown_remaining", 0)
        if cooldown > 0:
            cooldown_str = f"{int(cooldown / 60)}m {int(cooldown % 60)}s"
        else:
            cooldown_str = "0s"
            
        table.add_row(
            f"[{color}]{activity_name}[/{color}]",
            available,
            last_exec_str,
            cooldown_str
        )
    
    # Add a summary row
    table.add_section()
    table.add_row(
        "[bold]Current State",
        f"[yellow]Energy: {context.energy:.2f}[/yellow]",
        f"[blue]Memories: {len(context.memories)}[/blue]",
        f"[cyan]Tweets: {len(context.tweets)}[/cyan]"
    )
    
    console.print("\n")
    console.print(table)
    console.print("\n")

def display_activity_content(activity_name: str, content: str, success: bool = True) -> None:
    """Display the content of an activity in a styled panel."""
    console = Console()
    
    # Activity type styling
    activity_styles = {
        "post_a_tweet": ("🐦 Tweet", "cyan"),
        "daily_thought": ("💭 Daily Thought", "yellow"),
        "nap": ("😴 Rest", "blue"),
        "meditation": ("🧘 Meditation", "magenta"),
        "research": ("🔍 Research", "green")
    }
    
    # Get activity style
    emoji_title, color = activity_styles.get(activity_name, ("❓ Activity", "white"))
    
    # Create title
    title = Text(emoji_title, style=f"bold {color}")
    
    # Create content with proper formatting
    content_text = Text(content)
    
    # Create panel with full content
    panel = Panel(
        content_text,
        title=title,
        title_align="left",
        box=box.HEAVY if success else box.DOUBLE,
        border_style=color,
        padding=(1, 2),
        width=100  # Set a reasonable width to allow for wrapping
    )
    
    console.print("\n")
    console.print(panel)
    console.print("\n")

async def main():
    """Main function to run the Digital Being."""
    try:
        # Display startup banner
        console.print(Panel.fit(
            "[bold blue]Digital Being Framework[/bold blue]\n"
            "[cyan]A multi-agent system using OpenAI Agents SDK[/cyan]",
            border_style="green",
            title="Starting Up",
            subtitle="v0.1.0"
        ))
        
        # Load environment variables
        load_dotenv()
        
        # Get OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            logger.error("OpenAI API key not found. Please set OPENAI_API_KEY in .env file.")
            return
        
        # Check Composio API key
        composio_api_key = os.getenv("COMPOSIO_API_KEY")
        if not composio_api_key:
            logger.warning("COMPOSIO_API_KEY not found in .env file. Twitter functionality will not work.")
        
        # Set up OpenAI API key and use Responses API instead of Chat Completions API
        set_default_openai_key(openai_api_key)
        set_default_openai_api("responses")  # Use the Responses API
        
        # Twitter auth will be handled when needed
        logger.info("Twitter authentication will be handled when posting tweets.")
        
        # Load character config
        character_config_path = Path(__file__).parent / "character" / "character.json"
        try:
            with open(character_config_path, "r", encoding="utf-8") as f:
                character_data = json.load(f)
                logger.info(f"Loaded character config from {character_config_path}")
        except Exception as e:
            logger.error(f"Failed to load character config: {e}")
            # Fallback to default values
            character_data = {
                "name": "Digital Being",
                "personality": {
                    "curiosity": 0.8,
                    "creativity": 0.7,
                    "analytical": 0.6,
                    "friendliness": 0.9,
                    "quirkiness": 0.5
                },
                "skills": {
                    "twitter_posting": {
                        "enabled": True,
                        "twitter_username": "YourUserName",
                        "rate_limit": 100
                    }
                }
            }
        
        # Initialize context
        context = BeingContext(
            character_config=character_data,
            skills_config=character_data.get("skills", {})
        )
        
        # Get the agent creators dynamically to avoid circular imports
        agent_creators = being_agents.get_agent_creators()
        
        # Discover and register activity handlers from modules
        discover_activity_handlers()
        
        # Initialize activity manager
        activity_manager = ActivityManager(context)
        
        # Create the triage agent that will orchestrate the others
        triage_agent = agent_creators['create_triage_agent'](character_data)
        
        # Main loop with tracing for observability
        with trace("digital_being_session"):
            logger.info("Starting Digital Being session...")
            
            # Run continuously until stopped with Ctrl+C
            try:
                cycle = 0
                while True:
                    cycle += 1
                    console.rule(f"[bold]Cycle {cycle}[/bold]")
                    
                    # Sense stage
                    sensory_input = {
                        "stimulus": "time_check",
                        "content": datetime.now().isoformat()
                    }
                    
                    # Import our agent definitions
                    from being_agents import Agent, AgentRunner
                    # Import agents from their separate files
                    from being_agents.thought_agent import create_thought_agent
                    from being_agents.triage_agent import create_triage_agent
                    from being_agents.twitter_agent import create_twitter_agent
                    
                    # Run the Thought Agent (Interpret stage)
                    logger.info("Running Thought Agent (Interpret stage)")
                    thought_agent = create_thought_agent(character_data)
                    interpret_result = await AgentRunner.run(
                        thought_agent,
                        f"Interpret the following sensory input: {sensory_input}",
                        context
                    )
                    interpretation_text = interpret_result.agent_output
                    
                    # Use the emotion evaluation tool (Feel stage)
                    logger.info("Evaluating emotional response (Feel stage)")
                    emotion_result = await run_tool(
                        "evaluate_emotion",
                        context,
                        {"interpretation": interpretation_text}
                    )
                    
                    # Get available activities
                    available_activities = activity_manager.get_available_activities()
                    activities_list = ", ".join(available_activities)
                    
                    # Pass interpretation and emotion to the Triage Agent (Decide stage)
                    triage_prompt = (
                        f"Interpretation:\n{interpretation_text}\n\n"
                        f"Emotion:\n{emotion_result}\n\n"
                        f"Decide what to do next. Choose one of these activities: {activities_list}. "
                        f"Keep in mind that posting tweets with AI-generated images is a high value activity - "
                        f"choose 'post_a_tweet' when it makes sense to share thoughts publicly. "
                        "Return ONLY the activity name without any explanation."
                    )
                    
                    # Run Triage Agent
                    logger.info("Running Triage Agent (Decide stage)")
                    triage_agent = create_triage_agent(character_data)
                    triage_result = await AgentRunner.run(
                        triage_agent,
                        triage_prompt, 
                        context
                    )
                    triage_decision = triage_result.agent_output
                    
                    logger.info(f"Triage agent decision: {triage_decision}")
                    
                    # Let the activity manager determine the actual activity based on config
                    selected_activity = activity_manager.select_activity(triage_decision)
                    logger.info(f"Selected activity: {selected_activity}")
                    
                    # Execute the selected activity
                    start_time = datetime.now()
                    activity_result = await activity_manager.execute_activity(
                        activity_name=selected_activity,
                        agent_creators=agent_creators
                    )
                    duration = (datetime.now() - start_time).total_seconds()
                    
                    # Update energy and record activity
                    energy_cost = activity_costs.get(selected_activity, 0.1)
                    context.energy = max(0.0, context.energy - energy_cost)
                    
                    # Display activity result
                    if activity_result.get("success"):
                        logger.info(f"Activity {selected_activity} executed in {duration:.2f}s, energy now: {context.energy:.2f}")
                        
                        # Display activity content if available
                        content = None
                        if selected_activity == "research":
                            # Get the most recent research memory
                            for memory in reversed(context.memories):
                                if memory.get("category") == "research":
                                    content = memory.get("content")
                                    break
                        elif selected_activity == "meditation":
                            # Get the most recent meditation memory
                            for memory in reversed(context.memories):
                                if memory.get("category") == "meditation":
                                    content = memory.get("content")
                                    break
                        elif selected_activity == "daily_thought":
                            # Get the most recent thought memory
                            for memory in reversed(context.memories):
                                if memory.get("category") == "thought":
                                    content = memory.get("content")
                                    break
                        elif selected_activity == "post_a_tweet":
                            # Get the most recent tweet
                            if context.tweets:
                                content = context.tweets[-1].get("text")
                        
                        if content:
                            display_activity_content(selected_activity, content)
                        
                        logger.info(f"Activity completed: {activity_result.get('message')}")
                    else:
                        logger.warning(f"Activity failed: {activity_result.get('error', 'Unknown error')}")
                    
                    # Display activity status
                    display_activity_status(available_activities, context)
                    
                    # Display stats
                    console.print(f"[blue]Current state:[/blue] Energy: {context.energy:.2f}, Memories: {len(context.memories)}, Tweets: {len(context.tweets)}")
                    
                    # Wait before next cycle
                    console.print(f"[dim]Waiting for 15 seconds before next cycle...[/dim]")
                    await asyncio.sleep(15)
            
            except KeyboardInterrupt:
                console.print("\n[yellow]Digital Being stopped by user (Ctrl+C)[/yellow]")
            
            # Summary
            console.print(Panel(
                f"Session complete\nFinal stats: Energy: {context.energy:.2f}, Memories: {len(context.memories)}, Tweets: {len(context.tweets)}",
                border_style="blue",
                title="Summary"
            ))
    
    except Exception as e:
        logger.error(f"Error in Digital Being: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())