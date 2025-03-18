"""
Quick script to debug and fix the tools issue
"""

import sys
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("fix_tools")

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from digital_being.tools import _tools_registry, get_all_tools

def fix_tool_schemas():
    """Inspect and fix tool schemas"""
    tools = get_all_tools()
    logger.info(f"Found {len(tools)} tools")
    
    for i, tool in enumerate(tools):
        logger.info(f"Tool {i+1}:")
        if isinstance(tool, dict) and "function" in tool and "name" in tool.get("function", {}):
            logger.info(f"  Name: {tool['function']['name']}")
        else:
            logger.info(f"  Invalid tool format: {tool}")
    
    # Print a minimal valid tool schema for reference
    minimal_valid = {
        "type": "function",
        "function": {
            "name": "example_tool",
            "description": "Example tool",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
    
    logger.info(f"Minimal valid tool schema: {json.dumps(minimal_valid, indent=2)}")
    
    return "Tool inspection complete"

if __name__ == "__main__":
    fix_tool_schemas()