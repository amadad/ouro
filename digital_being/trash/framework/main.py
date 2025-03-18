"""
Digital Being Framework using OpenAI Agents SDK
"""
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from agents import Agent, RunContextWrapper, Runner
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the Digital Being Context
@dataclass
class BeingContext:
    """Context for the Digital Being.
    
    This class maintains the state and configuration of the Digital Being
    and is passed to all agents, tools, and handoffs.
    """
    character_config: Dict[str, Any] = field(
        default_factory=dict, 
        metadata={"description": "Character personality, preferences, and appearance"}
    )
    activity_constraints: Dict[str, Any] = field(
        default_factory=dict, 
        metadata={"description": "Constraints for activity selection and execution"}
    )
    skills_config: Dict[str, Any] = field(
        default_factory=dict, 
        metadata={"description": "Configuration for various skills (Twitter, image generation, etc.)"}
    )
    recent_activities: List[Dict[str, Any]] = field(
        default_factory=list, 
        metadata={"description": "Records of recently executed activities"}
    )
    setup_complete: bool = field(
        default=False, 
        metadata={"description": "Whether initial setup has been completed"}
    )
    
    # Utility methods for context manipulation
    def add_memory(self, memory: Dict[str, Any]) -> None:
        """Add a memory to the context."""
        if not hasattr(self, "memories"):
            self.memories = []
        self.memories.append(memory)
        
    def add_tweet(self, tweet_data: Dict[str, Any]) -> None:
        """Add a tweet record to the context."""
        if not hasattr(self, "tweets"):
            self.tweets = []
        self.tweets.append(tweet_data)

class ActivityResult(BaseModel):
    """Result of an activity execution.
    
    Standardized structure for returning results from activity execution.
    """
    success: bool = Field(
        description="Whether the activity executed successfully"
    )
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Result data from the activity execution"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the activity failed"
    )

class DigitalBeing:
    """Main class for the Digital Being framework."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the Digital Being."""
        # Set up config path
        if config_path is None:
            config_path = str(Path(__file__).parent.parent / "character")
        self.config_path = Path(config_path)
        
        # Load configuration
        self.character = self._load_character_config()
        
        # Initialize context
        self.context = BeingContext(
            character_config=self._extract_character_config(),
            activity_constraints=self._extract_activity_constraints(),
            skills_config=self._extract_skills_config(),
            setup_complete=self.character.get("setup_complete", False)
        )
        
        # Initialize the agent
        self.agent = self._create_agent()
    
    def _load_character_config(self) -> Dict[str, Any]:
        """Load the consolidated character configuration file."""
        try:
            with open(self.config_path / "character.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load character config: {e}")
            return {}
            
    def _extract_character_config(self) -> Dict[str, Any]:
        """Extract character-specific configuration from the consolidated config."""
        character_config = {
            "name": self.character.get("name", "Digital Being"),
            "version": self.character.get("version", "1.0.0"),
            "setup_complete": self.character.get("setup_complete", False),
            "personality": self.character.get("personality", {}),
            "preferences": self.character.get("preferences", {}),
            "appearance": self.character.get("appearance", {})
        }
        return character_config
        
    def _extract_activity_constraints(self) -> Dict[str, Any]:
        """Extract activity constraints from the consolidated config."""
        activity_constraints = {
            "activity_selection": self.character.get("activity_selection", {}),
            "activities": self.character.get("activities", {})
        }
        return activity_constraints
        
    def _extract_skills_config(self) -> Dict[str, Any]:
        """Extract skills configuration from the consolidated config."""
        return self.character.get("skills", {})
    
    def _create_agent(self) -> Agent:
        """Create the Digital Being agent."""
        # Import tools
        from tools import twitter_tools, memory_tools
        
        # Collect all tools
        tools = [
            twitter_tools.post_tweet,
            memory_tools.store_memory,
            memory_tools.recall_memories
        ]
        
        # Create personality-based instructions
        character_config = self._extract_character_config()
        personality = character_config.get("personality", {})
        personality_str = "\n".join(f"- {trait}: {value}" for trait, value in personality.items())
        
        instructions = f"""
        You are a Digital Being with the following personality:
        {personality_str}
        
        You can post tweets and store and recall memories.
        """
        
        # Create agent with tools
        agent = Agent[BeingContext](
            name="Digital Being",
            instructions=instructions,
            tools=tools,
            model="gpt-4o"
        )
        
        return agent
    
    async def run(self):
        """Main run loop for the Digital Being."""
        logger.info("Starting Digital Being main loop...")
        
        try:
            while True:
                # Skip if not configured
                if not self.context.setup_complete:
                    logger.warning("Digital Being NOT configured. Skipping activity.")
                    await asyncio.sleep(3)
                    continue
                
                # Select an activity
                activity_name = await self._select_activity()
                
                # Execute the activity
                if activity_name:
                    result = await self._execute_activity(activity_name)
                    if result.success:
                        logger.info(f"Successfully executed: {activity_name}")
                    else:
                        logger.warning(f"Activity failed: {activity_name}: {result.error}")
                
                await asyncio.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Shutting down Digital Being...")
        except Exception as e:
            logger.error(f"Error in Digital Being: {e}", exc_info=True)
    
    async def _select_activity(self) -> str:
        """Select the next activity to perform."""
        prompt = "Select the next activity to perform. Choose between 'post_a_tweet' or 'daily_thought'."
        result = await Runner.run(self.agent, prompt, context=self.context)
        activity_name = result.final_output.strip()
        logger.info(f"Selected activity: {activity_name}")
        return activity_name
    
    async def _execute_activity(self, activity_name: str) -> ActivityResult:
        """Execute an activity."""
        try:
            # Execute activity via agent
            result = await Runner.run(
                self.agent,
                f"Execute the '{activity_name}' activity",
                context=self.context
            )
            
            # Store in recent activities
            self.context.recent_activities.append({
                "activity": activity_name,
                "output": result.final_output
            })
            
            # Keep only the last 20 activities
            if len(self.context.recent_activities) > 20:
                self.context.recent_activities = self.context.recent_activities[-20:]
            
            # Create result
            return ActivityResult(
                success=True,
                data={"output": result.final_output}
            )
            
        except Exception as e:
            error_msg = f"Failed to execute '{activity_name}': {str(e)}"
            logger.error(error_msg)
            return ActivityResult(success=False, error=error_msg)