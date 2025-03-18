"""
Schema definitions for Digital Being.

This module contains data models and schema definitions for the Digital Being framework.
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class BeingContext:
    """Context object for the Digital Being."""
    character_config: Dict[str, Any] = field(default_factory=dict)
    skills_config: Dict[str, Any] = field(default_factory=dict)
    memories: List[Dict[str, Any]] = field(default_factory=list)
    tweets: List[Dict[str, Any]] = field(default_factory=list)
    energy: float = 1.0
    
    def add_memory(self, memory: Dict[str, Any]) -> None:
        """Add a memory and trim if too many."""
        self.memories.append(memory)
        if len(self.memories) > 100:
            self.memories = self.memories[-100:]
    
    def add_tweet(self, tweet: Dict[str, Any]) -> None:
        """Add a tweet and trim if too many."""
        self.tweets.append(tweet)
        if len(self.tweets) > 50:
            self.tweets = self.tweets[-50:]
    
    def get_personality(self) -> Dict[str, float]:
        """Get personality traits from character config."""
        return self.character_config.get("personality", {})
        
    def get_recent_memories(self, category: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent memories, optionally filtered by category."""
        memories = self.memories
        if category:
            memories = [m for m in memories if m.get("category") == category]
        # Sort by recency
        memories.sort(key=lambda m: m.get("timestamp", ""), reverse=True)
        return memories[:limit]