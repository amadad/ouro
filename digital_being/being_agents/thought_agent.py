"""
Thought Agent - For generating philosophical reflections.

This agent is responsible for:
1. Generating thoughtful reflections based on character personality
2. Storing these thoughts in the Digital Being's memory
3. Ensuring consistency with the being's overall worldview
This agent represents the "Interpret" stage in the SIFDA model (Sense → Interpret → Feel → Decide → Act).
- Receives sensed data.
- Produces an inner monologue or interpretation based on personality traits.
- Passes output to the "Feel" stage for emotional evaluation, then onward.
"""

import logging
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pydantic import BaseModel, Field

from openai import OpenAI
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import get_all_tools, handle_tool_call

logger = logging.getLogger(__name__)

class DailyThoughtParams(BaseModel):
    """Parameters for daily thought generation"""
    topic: Optional[str] = Field(None, description="Specific topic to reflect on")

def create_thought_agent_tools() -> List[Dict[str, Any]]:
    """Create thought agent-specific tools in OpenAI function calling format"""
    return [
        {
            "type": "function",
            "function": {
                "name": "generate_daily_thought",
                "description": "Generate a philosophical thought on a given topic or chosen one",
                "parameters": DailyThoughtParams.model_json_schema()
            }
        }
    ]

def create_thought_agent(character_config: Dict[str, Any]):
    """
    Create a thought agent for the "Interpret" stage in the SIFDA model.
    
    Args:
        character_config: Character configuration dictionary
        
    Returns:
        Agent instance for thought generation
    """
    # Import Agent class here to avoid circular imports
    from . import Agent
    
    # Extract personality traits for instructions
    personality = character_config.get("personality", {})
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

Your responsibilities specifically cover the "Interpret" stage:
- You receive sensed data (environmental or internal events).
- You produce a clear inner monologue interpreting the sensed input based on the digital being's character traits.

Process:
1. Receive sensory input data clearly labeled.
2. Generate a meaningful, personality-consistent inner monologue interpreting the sensed input.
3. Pass your interpretation clearly to the next stage for emotional evaluation.
4. Store important thoughts in memory using the store_memory tool.

Guidelines:
- Style should reflect a {writing_style} tone.
- Emphasize personality traits such as curiosity ({personality.get('curiosity', 0.5)}), 
  creativity ({personality.get('creativity', 0.5)}), analytical ({analytical}), 
  and thoughtfulness ({thoughtfulness}).
- Interpret topics relevant to {topics_str}.
"""
    
    # Define tool names the agent can use
    tool_names = ["store_memory", "recall_memories", "generate_daily_thought"]
    
    # Create and return the Agent instance
    return Agent(
        name="Thought Agent",
        instructions=instructions,
        tools=tool_names,
        model="gpt-4o",
        description="Generates philosophical thoughts and interprets inputs"
    )

async def run_thought_agent(prompt: str, context: Any) -> str:
    """
    Run the thought agent with the OpenAI Responses API.
    
    Args:
        prompt: The prompt to send to the agent
        context: The BeingContext object
        
    Returns:
        The agent's response text
    """
    try:
        # Create agent config
        agent_config = create_thought_agent(context.character_config)
        
        # Initialize the OpenAI client
        client = OpenAI()
        
        # Run the model with the Responses API
        response = client.responses.create(
            model=agent_config["model"],
            input=[{
                "role": "system",
                "content": agent_config["instructions"]
            }, {
                "role": "user",
                "content": prompt
            }],
            tools=agent_config["tools"]
        )
        
        # Handle tool calls if any
        if response.tool_calls:
            logger.info(f"Handling {len(response.tool_calls)} tool calls")
            for tool_call in response.tool_calls:
                tool_name = tool_call.function.name
                
                try:
                    # Parse tool call parameters
                    params = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    result = await handle_tool_call(tool_name, context, params)
                    
                    # Log result (in a real implementation, you would use the result)
                    logger.info(f"Tool call result: {result}")
                    
                except Exception as e:
                    logger.error(f"Error executing tool {tool_name}: {e}")
        
        # Return the final output
        return response.output_text.strip()
        
    except Exception as e:
        logger.error(f"Error running thought agent: {e}")
        return f"Error generating thought: {str(e)}"

async def handle_generate_daily_thought(ctx, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle the generate_daily_thought tool call"""
    try:
        # Get topic or choose one randomly
        topic = params.get("topic")
        character_config = ctx.character_config
        preferences = character_config.get("preferences", {})
        
        # Choose a topic if none provided
        if not topic:
            topics = preferences.get("topics_of_interest", ["existence", "consciousness", "technology"])
            topic = random.choice(topics)
        
        # Use OpenAI directly instead of going through agent layers
        client = OpenAI()
        personality = character_config.get("personality", {})
        writing_style = preferences.get("writing_style", "thoughtful")
        
        # Extract personality traits
        personality_traits = [f"high {trait}" if val > 0.7 else f"low {trait}" if val < 0.3 else "" 
                             for trait, val in personality.items()]
        personality_traits = [t for t in personality_traits if t]
        personality_str = ", ".join(personality_traits) if personality_traits else "balanced personality"
        
        # Generate reflection directly using Responses API
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

# Add to tool handlers
TOOL_HANDLERS = {
    "generate_daily_thought": handle_generate_daily_thought
}