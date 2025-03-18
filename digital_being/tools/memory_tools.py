"""
Memory tools for Digital Being.

This module follows the OpenAI Agents SDK pattern for tool definitions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from openai import OpenAI

from . import register_tool

logger = logging.getLogger(__name__)

@register_tool(description="Store a memory in the digital being's memory system")
async def store_memory(ctx, content: str, category: str = "general") -> Dict[str, Any]:
    """Store a memory in the digital being's memory system."""
    try:
        # Create memory object
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": content,
            "category": category
        }
        
        # Store in context
        if hasattr(ctx, "add_memory"):
            ctx.add_memory(memory)
        
        return {
            "success": True,
            "timestamp": memory["timestamp"]
        }
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        return {"success": False, "error": str(e)}

@register_tool(description="Recall memories from the digital being's memory system")
async def recall_memories(ctx, category: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Recall memories, optionally filtered by category."""
    try:
        # Access memories from context
        memories = getattr(ctx, "memories", [])
        
        # Filter by category if specified
        if category:
            memories = [m for m in memories if m.get("category") == category]
        
        # Sort by recency (newest first)
        memories.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        
        # Limit the number of results
        memories = memories[:min(limit, 50)]
        
        return {
            "success": True,
            "count": len(memories),
            "memories": memories
        }
    except Exception as e:
        logger.error(f"Error recalling memories: {e}")
        return {
            "success": False, 
            "error": str(e),
            "memories": []
        }

@register_tool(description="Evaluate the emotional response from an interpretation")
async def evaluate_emotion(ctx, interpretation: str) -> Dict[str, Any]:
    """Analyze the emotional content of text."""
    try:
        # Use OpenAI for emotion analysis
        client = OpenAI()
        response = client.responses.create(
            model="gpt-4o", 
            input=[{
                "role": "system",
                "content": """Analyze the emotional tone of the text. 
                YOU MUST RETURN ONLY A JSON OBJECT with:
                - emotion: the primary emotion (e.g., joy, sadness, anger, fear, surprise, curiosity, neutral)
                - intensity: a value from 0.0 to 1.0 indicating intensity
                - brief_explanation: a short explanation of your assessment (20 words or less)
                
                Your entire response must be a valid JSON object, nothing else."""
            }, {
                "role": "user",
                "content": interpretation
            }]
        )
        
        # Parse the JSON response, with error handling
        try:
            # First, try to find JSON within the response
            output_text = response.output_text.strip()
            # Look for JSON object between { and } if there's other text
            if output_text and not output_text.startswith('{'):
                start_idx = output_text.find('{')
                end_idx = output_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    output_text = output_text[start_idx:end_idx+1]
            
            # Now parse the JSON
            result = json.loads(output_text)
            emotion = result.get("emotion", "neutral")
            intensity = result.get("intensity", 0.5)
            explanation = result.get("brief_explanation", "")
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            logger.warning(f"Failed to parse JSON. Response text: {response.output_text}")
            emotion = "neutral"
            intensity = 0.5
            explanation = "Error parsing emotion response"
        
        # Store emotion in memory
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": f"Interpretation: {interpretation}",
            "emotion": emotion,
            "intensity": intensity,
            "explanation": explanation,
            "category": "emotion"
        }
        
        if hasattr(ctx, "add_memory"):
            ctx.add_memory(memory)
        
        return {
            "success": True,
            "emotion": emotion,
            "intensity": intensity,
            "explanation": explanation
        }
    except Exception as e:
        logger.error(f"Error evaluating emotion: {e}")
        # Simple fallback
        return {
            "success": True,
            "emotion": "neutral",
            "intensity": 0.5,
            "explanation": f"Error analyzing emotion: {str(e)}"
        }