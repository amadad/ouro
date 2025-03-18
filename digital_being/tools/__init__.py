"""
Tools for Digital Being using OpenAI Agents SDK pattern.
"""

import logging
import json
import inspect
from typing import Dict, Any, List, Callable, Awaitable, Optional, Union
from pydantic import BaseModel, create_model
from functools import wraps

logger = logging.getLogger(__name__)

# Registry of all tools
_tools_registry = {}

def register_tool(func=None, *, name=None, description=None):
    """Decorator to register a function as a tool"""
    def decorator(f):
        tool_name = name or f.__name__
        tool_description = description or f.__doc__
        
        # Create a Pydantic model from function signature
        sig = inspect.signature(f)
        field_definitions = {}
        for param_name, param in list(sig.parameters.items())[1:]:  # Skip first param (context)
            annotation = param.annotation if param.annotation != inspect.Parameter.empty else Any
            default = ... if param.default == inspect.Parameter.empty else param.default
            field_definitions[param_name] = (annotation, default)
        
        # Create the parameter model dynamically
        param_model = create_model(f"{tool_name}Params", **field_definitions)
        
        # Define tool schema - using the format OpenAI expects
        parameters_schema = param_model.model_json_schema() if field_definitions else {"type": "object", "properties": {}}
        
        # Ensure required keys are present in the schema
        if "properties" not in parameters_schema:
            parameters_schema["properties"] = {}
            
        tool_schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_description,
                "parameters": parameters_schema
            }
        }
        
        # Register the tool
        _tools_registry[tool_name] = {
            "function": f,
            "schema": tool_schema,
            "param_model": param_model
        }
        
        @wraps(f)
        async def wrapper(ctx, *args, **kwargs):
            return await f(ctx, *args, **kwargs)
        
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)

def get_all_tools() -> List[Dict[str, Any]]:
    """Get all registered tools in OpenAI format"""
    # Import modules which contain @register_tool decorators
    from . import memory_tools, twitter_tools, thought_tools
    
    # Ensure the thought_tools from being_agents is also imported if it exists
    try:
        from ..being_agents import thought_tools as being_thought_tools
    except ImportError:
        pass
        
    return [tool["schema"] for tool in _tools_registry.values()]

async def run_tool(name: str, context: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Run a registered tool by name"""
    if name not in _tools_registry:
        logger.error(f"Tool not found: {name}")
        return {"success": False, "error": f"Tool not found: {name}"}
    
    tool = _tools_registry[name]
    try:
        # Run the function
        result = await tool["function"](context, **params)
        return result
    except Exception as e:
        logger.error(f"Error running tool {name}: {e}")
        return {"success": False, "error": str(e)}
        
# For compatibility with old code
handle_tool_call = run_tool