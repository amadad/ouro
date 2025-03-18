import sys
import os
import json

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import our modules
from digital_being.tools import register_tool

# Create a dummy tool for testing
@register_tool(description="Test tool")
async def test_tool(ctx, param1: str = "default"):
    return {"success": True, "param": param1}

# Print the tool schema
from digital_being.tools import _tools_registry
print(json.dumps(_tools_registry["test_tool"]["schema"], indent=2))