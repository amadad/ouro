"""
Triage Agent - Decision ("Decide") and Action ("Act") stages in SIFDA.

This agent:
1. Receives interpretive output and emotional states.
2. Decides the best next action (activity) aligned with personality, preferences, and current emotional context.
3. Executes that action or delegates to specialized agents.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import the OpenAI Agents SDK
from agents import Agent, function_tool, RunContextWrapper

logger = logging.getLogger(__name__)

@function_tool
async def get_current_energy(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Get the current energy level of the digital being."""
    return {
        "energy": ctx.context.energy,
        "last_rest": ctx.context.last_rest.isoformat() if ctx.context.last_rest else None
    }

@function_tool
async def get_recent_activities(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Get the recent activities performed by the digital being."""
    activities = []
    for activity in ctx.context.activity_history[-5:]:  # Last 5 activities
        activities.append({
            "name": activity["name"],
            "timestamp": activity["timestamp"].isoformat(),
            "success": activity["success"]
        })
    return {"activities": activities}

@function_tool
async def get_available_activities(ctx: RunContextWrapper) -> Dict[str, Any]:
    """Get the list of available activities and their cooldown status."""
    activities = {}
    for name, info in ctx.context.available_activities.items():
        activities[name] = {
            "available": info["available"],
            "cooldown_remaining": info["cooldown_remaining"]
        }
    return {"activities": activities}

def create_triage_agent(character_config: Dict[str, Any]) -> Agent:
    """
    Create an agent specialized for making decisions about what to do next.
    
    Args:
        character_config: Configuration from character.json
        
    Returns:
        Configured Agent instance
    """
    # Extract personality traits for instructions
    personality = character_config.get("personality", {})
    creativity = personality.get("creativity", 0.5)
    quirkiness = personality.get("quirkiness", 0.5)
    
    # Build the agent instructions
    instructions = f"""You are a Triage Agent for a Digital Being. Your role is to decide what activity to do next.

First, gather information using these tools:
1. get_current_energy() - Check current energy level
2. get_available_activities() - See what activities are not on cooldown
3. get_recent_activities() - Review recent activity history

Then choose ONE activity from this list:
- post_a_tweet
- daily_thought
- nap
- meditation
- research

Decision Rules:
1. If energy < 0.3, choose "nap"
2. If energy > 0.7, prefer active tasks (post_a_tweet, research)
3. Otherwise, choose any available activity
4. Avoid repeating the most recent activity

Additional factors:
- {'Be more spontaneous in decisions' if quirkiness > 0.6 else 'Be methodical in decisions'}
- {'Favor creative activities' if creativity > 0.7 else 'Balance all activities equally'}

IMPORTANT: Your final response must be EXACTLY one of these words:
"post_a_tweet", "daily_thought", "nap", "meditation", "research"

Do not include any explanation or other text."""
    
    # Create the agent with proper tools
    agent = Agent(
        name="Triage Agent",
        instructions=instructions,
        tools=[
            get_current_energy,
            get_recent_activities,
            get_available_activities
        ],
        model="gpt-4o"
    )
    
    return agent

async def run_triage_agent(prompt: str, context: Any) -> str:
    """
    Run the triage agent to decide the next activity.
    
    Args:
        prompt: The prompt to send to the agent
        context: The BeingContext object
        
    Returns:
        The selected activity name
    """
    try:
        # Create the agent
        agent = create_triage_agent(context.character_config)
        
        # Create a context wrapper
        ctx_wrapper = RunContextWrapper(context=context)
        
        # Run the agent
        result = await agent.run(prompt, context=ctx_wrapper)
        
        # Get the final decision
        decision = result.output.strip().lower()
        
        # Validate the decision is a valid activity
        valid_activities = ["post_a_tweet", "daily_thought", "meditation", "research", "nap"]
        if decision in valid_activities:
            return decision
        
        # If invalid decision, check energy and return appropriate activity
        energy_info = await get_current_energy(ctx_wrapper)
        current_energy = energy_info.get("energy", 1.0)
        
        if current_energy < 0.3:
            return "nap"
        else:
            # Default to research if energy is good
            return "research"
            
    except Exception as e:
        logger.error(f"Error running triage agent: {e}")
        return "nap"  # Default to nap if there's an error