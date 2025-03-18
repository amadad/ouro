"""
Composio Connection Management

Simple utility to check and ensure Composio connections are available.
"""

import os
import json
import subprocess
import time
from pathlib import Path
import logging
from typing import Optional, Dict, Any, List

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

try:
    from composio_openai import ComposioToolSet
except ImportError:
    logging.warning("composio_openai not installed. Some features will be unavailable.")

logger = logging.getLogger(__name__)
console = Console()

# Default OAuth file path
DEFAULT_OAUTH_FILE = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / "storage" / "composio_oauth.json"

# Connection cache
_connections = {}
_toolset = None

def _load_connections(oauth_file: Path = DEFAULT_OAUTH_FILE) -> Dict[str, Any]:
    """Load connection data from OAuth file."""
    global _connections
    
    if not oauth_file.exists():
        return {}
    
    try:
        with open(oauth_file, 'r') as f:
            _connections = json.load(f)
        return _connections
    except Exception as e:
        logger.warning(f"Error loading OAuth file: {e}")
        return {}

def _get_toolset() -> Optional[Any]:
    """Get or initialize the Composio toolset."""
    global _toolset
    
    if _toolset is not None:
        return _toolset
    
    api_key = os.getenv("COMPOSIO_API_KEY")
    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set in environment variables")
        return None
    
    try:
        _toolset = ComposioToolSet(api_key=api_key)
        return _toolset
    except Exception as e:
        logger.error(f"Error initializing Composio toolset: {e}")
        return None

def is_connected(app_name: str) -> bool:
    """
    Check if a specific app is connected.
    
    Args:
        app_name: Name of the app (e.g., "TWITTER", "LINKEDIN")
        
    Returns:
        True if connected, False otherwise
    """
    global _connections
    
    # Load connections if not loaded yet
    if not _connections:
        _load_connections()
    
    # Check in local cache
    if app_name in _connections:
        return _connections[app_name].get("connected", False)
    
    return False

def ensure_connection(app_name: str, interactive: bool = True) -> bool:
    """
    Check if connected to an app, and connect if not.
    
    Args:
        app_name: Name of the app (e.g., "TWITTER", "LINKEDIN")
        interactive: If True, prompt user for confirmation
        
    Returns:
        True if connected, False otherwise
    """
    # Normalize app name
    app_name = app_name.upper()
    
    # Check if already connected
    if is_connected(app_name):
        return True
    
    # Not connected, ask user if interactive
    if interactive:
        console.print(Panel(f"Not connected to {app_name}", style="yellow"))
        if not Confirm.ask("Do you want to connect now?"):
            console.print(f"Skipping {app_name} connection.", style="yellow")
            return False
    
    # Try to connect
    try:
        console.print(f"Launching browser to authenticate with {app_name}...")
        process = subprocess.Popen(['composio', 'add', app_name.lower()])
        process.wait()
        
        # Wait for connection to register
        time.sleep(2)
        
        # Check if successful by loading connections again
        _load_connections()
        
        if is_connected(app_name):
            console.print(f"Successfully connected to {app_name}!", style="green")
            return True
        else:
            console.print(f"Failed to connect to {app_name}. Please try again.", style="red")
            return False
    
    except Exception as e:
        logger.error(f"Error connecting to {app_name}: {e}")
        return False

# Load connections at import time
_load_connections()