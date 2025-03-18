"""
Composio Integration for Digital Being

Simple interface to execute Composio actions.
"""
import logging
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from composio_openai import ComposioToolSet
except ImportError as e:
    raise ImportError(f"Failed to import Composio: {e}. Please install with 'pip install composio-openai'")

logger = logging.getLogger(__name__)

# Singleton variables
_toolset = None
_initialized = False
_entity_id = "MyDigitalBeing"
_oauth_file_path = Path(os.path.dirname(os.path.dirname(__file__))) / "storage" / "composio_oauth.json"

def initialize() -> bool:
    """Initialize the Composio toolset."""
    global _toolset, _initialized
    
    try:
        # Get API key from environment
        api_key = os.getenv("COMPOSIO_API_KEY")
        
        if not api_key:
            logger.error("COMPOSIO_API_KEY environment variable not set. Please set this in your .env file.")
            return False
        
        # Create toolset
        _toolset = ComposioToolSet(api_key=api_key)
        _initialized = True
        logger.info("Composio integration initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize Composio: {e}")
        _initialized = False
        return False

def execute_action(action: str, params: Dict[str, Any], entity_id: str = _entity_id) -> Dict[str, Any]:
    """
    Execute a Composio action.
    
    Args:
        action: Action name (e.g., "TWITTER_CREATION_OF_A_POST")
        params: Parameters for the action
        entity_id: Entity ID for the action
        
    Returns:
        Response from Composio
    """
    global _toolset, _initialized
    
    if not _initialized or not _toolset:
        if not initialize():
            return {"success": False, "error": "Composio not initialized. Check COMPOSIO_API_KEY environment variable."}
    
    try:
        # Log action
        if action == "TWITTER_CREATION_OF_A_POST":
            logger.info(f"Posting tweet via Composio: {params.get('text', '')[:30]}...")
        elif action == "TWITTER_MEDIA_UPLOAD_MEDIA":
            logger.info(f"Uploading media to Twitter via Composio")
        else:
            logger.info(f"Executing Composio action: {action}")
        
        # Execute the action
        response = _toolset.execute_action(
            action=action,
            params=params,
            entity_id=entity_id
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error executing Composio action {action}: {e}")
        return {"success": False, "error": str(e)}

# Create a singleton instance for backward compatibility
class ComposioManager:
    """Manager for Composio integration (for backward compatibility)."""
    
    def __init__(self):
        """Initialize the manager."""
        self.initialized = _initialized
    
    def initialize(self) -> bool:
        """Initialize the Composio toolset."""
        return initialize()
    
    def execute_action(self, action: str, params: Dict[str, Any], entity_id: str) -> Dict[str, Any]:
        """Execute a Composio action."""
        return execute_action(action, params, entity_id)

# Create the singleton for backward compatibility
composio_manager = ComposioManager()