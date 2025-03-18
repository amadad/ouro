"""
Logging configuration for the Digital Being.
Provides colored console output with configurable verbosity levels using Rich.
"""
import logging
import sys
from typing import Dict, Any, Optional

from rich.console import Console
from rich.logging import RichHandler

def configure_logging(verbose: bool = False) -> None:
    """
    Configure the logging system with beautiful colored output using Rich.
    
    Args:
        verbose: If True, show DEBUG level logs, otherwise INFO and above
    """
    # Rich console configuration
    console = Console()
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Rich console handler
    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        show_time=False,
        show_path=False,
    )
    rich_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    root_logger.addHandler(rich_handler)
    
    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING) 