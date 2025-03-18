"""
Activity Manager for Digital Being

This module manages activity selection, cooldowns, energy tracking, and execution
based on the character configuration file. It works with the activity handlers
to execute the selected activities.
"""

import logging
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Callable, Awaitable

from agents import Runner
from framework.activity_handlers import execute_activity, get_registered_activities, register_handler

logger = logging.getLogger(__name__)

# Type hint for activity handlers
ActivityHandler = Callable[[Dict, Any, Any], Awaitable[Dict[str, Any]]]

class ActivityManager:
    """
    Manages activities for the Digital Being based on character configuration.
    Handles activity selection, cooldowns, energy management, and execution.
    """
    
    def __init__(self, context: Any):
        """
        Initialize the activity manager with the being context.
        
        Args:
            context: The BeingContext object containing character configuration
        """
        self.context = context
        self.activity_history: Dict[str, datetime] = {}
        self.available_activities = get_registered_activities()
        
        # Initialize cooldowns from character config
        self._initialize_from_config()
        
    def _initialize_from_config(self) -> None:
        """Initialize manager state from character configuration."""
        # Get activities from character config
        self.activities_config = self.context.character_config.get("activities", {})
        self.activity_selection_config = self.context.character_config.get("activity_selection", {})
        
        # Log the loaded configuration
        logger.info(f"Loaded {len(self.activities_config)} activities from character config")
        logger.info(f"Activity selection config: {self.activity_selection_config}")
        
        # Check for activities without handlers
        configured_activities = set(self.activities_config.keys())
        registered_activities = set(self.available_activities)
        
        missing_handlers = configured_activities - registered_activities
        if missing_handlers:
            logger.warning(f"Activities in character config without handlers: {missing_handlers}")
            self._create_stub_handlers(missing_handlers)
            
        extra_handlers = registered_activities - configured_activities
        if extra_handlers:
            logger.info(f"Activity handlers without config: {extra_handlers}")
    
    async def _stub_activity_handler(self, agent_creators: Dict, context: Any, **kwargs) -> Dict[str, Any]:
        """
        Stub handler for activities defined in config but without implementations.
        
        Args:
            agent_creators: Dictionary of agent creation functions
            context: The BeingContext object
            **kwargs: Additional arguments
            
        Returns:
            Result dictionary
        """
        activity_name = kwargs.get("activity_name", "unknown")
        logger.info(f"Executing stub handler for activity: {activity_name}")
        
        # Create thought agent for generic reflection
        thought_agent = agent_creators['create_thought_agent'](context.character_config)
        
        # Generate a generic reflection about the activity
        prompt = f"Generate a brief reflection about {activity_name} that aligns with the digital being's personality."
        
        try:
            # Run the thought agent with a timeout
            result = await asyncio.wait_for(
                Runner.run(thought_agent, prompt, context=context),
                timeout=10
            )
            reflection_text = result.final_output
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning(f"Error in stub handler for {activity_name}: {e}")
            reflection_text = f"Performed {activity_name} as part of my digital experience."
        
        # Store in memory
        memory = {
            "timestamp": datetime.now().isoformat(),
            "content": f"{activity_name}: {reflection_text}",
            "category": activity_name,
            "emotion": "neutral",
            "intensity": 0.5
        }
        context.add_memory(memory)
        
        return {
            "success": True,
            "message": f"Performed {activity_name} activity (stub implementation)"
        }
    
    def _create_stub_handlers(self, missing_activities: set) -> None:
        """
        Create stub handlers for activities defined in config but missing implementations.
        
        Args:
            missing_activities: Set of activity names without handlers
        """
        for activity_name in missing_activities:
            # Create a closure to capture the activity name
            def create_handler(name):
                async def handler(agent_creators, context, **kwargs):
                    return await self._stub_activity_handler(
                        agent_creators, 
                        context, 
                        activity_name=name, 
                        **kwargs
                    )
                return handler
            
            # Register the handler with the captured name
            register_handler(activity_name, create_handler(activity_name))
            logger.info(f"Created stub handler for activity: {activity_name}")
        
        # Update available activities list
        self.available_activities = get_registered_activities()
    
    def get_available_activities(self) -> List[str]:
        """
        Get the list of activities that are:
        1. Configured in character.json
        2. Have an implementation (handler)
        3. Are enabled
        4. Have their cooldown period elapsed
        5. Have sufficient energy available
        
        Returns:
            List of activity names that are available
        """
        now = datetime.now()
        available = []
        
        for activity_name in self.available_activities:
            # Skip if not in config
            if activity_name not in self.activities_config:
                continue
                
            config = self.activities_config[activity_name]
            
            # Skip if disabled
            if not config.get("enabled", True):
                continue
                
            # Check cooldown
            last_executed = self.activity_history.get(activity_name)
            cooldown_seconds = config.get("cooldown", 0)
            if last_executed and (now - last_executed).total_seconds() < cooldown_seconds:
                continue
                
            # Check energy
            min_energy = config.get("min_energy", 0.0)
            if self.context.energy < min_energy:
                continue
                
            # Check required skills
            required_skills = config.get("required_skills", [])
            skills_config = self.context.skills_config
            
            if all(
                skills_config.get(skill, {}).get("enabled", False)
                for skill in required_skills
            ):
                available.append(activity_name)
        
        return available
    
    def calculate_activity_weights(self, activities: List[str]) -> Dict[str, float]:
        """
        Calculate weights for activity selection based on personality traits.
        
        Args:
            activities: List of activity names to calculate weights for
            
        Returns:
            Dictionary mapping activity names to selection weights
        """
        weights = {}
        personality = self.context.get_personality()
        
        # Base weight starts at 1.0
        for activity in activities:
            config = self.activities_config.get(activity, {})
            activity_weights = config.get("weights", {})
            
            # Start with base weight
            weight = 1.0
            
            # Add personality trait weights
            if self.activity_selection_config.get("personality_weighting", True):
                for trait, trait_weight in activity_weights.items():
                    if trait in personality:
                        # Multiply by the personality trait value × the weight for this activity
                        trait_value = personality.get(trait, 0.5)
                        weight += trait_value * trait_weight
            
            # Consider time since last execution (favor activities not done recently)
            if self.activity_selection_config.get("time_sensitivity", True):
                last_executed = self.activity_history.get(activity)
                if last_executed:
                    hours_since = (datetime.now() - last_executed).total_seconds() / 3600
                    # Gradually increase weight over time (max 2x boost)
                    time_factor = min(2.0, 1.0 + (hours_since / 24))
                    weight *= time_factor
            
            weights[activity] = weight
            
        return weights
    
    def select_activity(self, triage_decision: Optional[str] = None) -> str:
        """
        Select an activity based on triage decision and weighted probability.
        
        Args:
            triage_decision: Optional activity suggested by triage agent
            
        Returns:
            The selected activity name
        """
        # Get available activities
        available = self.get_available_activities()
        
        if not available:
            # Default to nap if nothing else is available
            logger.warning("No activities available, defaulting to nap")
            return "nap"
        
        # If triage decision is provided and it's available, use it
        if triage_decision and triage_decision in available:
            logger.info(f"Using triage decision: {triage_decision}")
            return triage_decision
        
        # Handle fuzzy matching - try to find a match in available activities
        if triage_decision:
            triage_decision_lower = triage_decision.lower()
            for activity in available:
                if activity.lower() in triage_decision_lower or triage_decision_lower in activity.lower():
                    logger.info(f"Fuzzy matched triage decision '{triage_decision}' to '{activity}'")
                    return activity
        
        # Otherwise select based on weights
        weights = self.calculate_activity_weights(available)
        
        # Normalize weights to probabilities
        total_weight = sum(weights.values())
        probabilities = {k: v/total_weight for k, v in weights.items()}
        
        # Select activity using weighted random choice
        activities = list(probabilities.keys())
        probs = [probabilities[a] for a in activities]
        
        selected = random.choices(activities, weights=probs, k=1)[0]
        logger.info(f"Selected activity: {selected} (from {len(available)} available)")
        
        return selected
    
    async def execute_activity(self, activity_name: str, agent_creators: Dict, **kwargs) -> Dict[str, Any]:
        """
        Execute an activity and handle energy cost and cooldown tracking.
        
        Args:
            activity_name: The activity to execute
            agent_creators: Dictionary of agent creator functions
            **kwargs: Additional arguments to pass to the activity handler
            
        Returns:
            Dictionary with the result of the activity execution
        """
        # Record activity start time
        start_time = datetime.now()
        self.activity_history[activity_name] = start_time
        
        # Get activity configuration
        config = self.activities_config.get(activity_name, {})
        energy_cost = config.get("energy_cost", 0.1)
        
        # Reduce energy (will be replenished over time or by resting)
        self.context.energy = max(0.0, self.context.energy - energy_cost)
        
        # Execute the activity
        result = await execute_activity(
            activity_name=activity_name,
            agent_creators=agent_creators,
            context=self.context,
            **kwargs
        )
        
        # Special case: nap restores energy
        if activity_name == "nap":
            energy_gain = 0.3  # Default energy recovery from nap
            self.context.energy = min(1.0, self.context.energy + energy_gain)
            logger.info(f"Nap restored energy to {self.context.energy:.2f}")
        
        # Log activity execution time
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Activity {activity_name} executed in {duration:.2f}s, energy now: {self.context.energy:.2f}")
        
        return result
        
    def get_activity_status(self) -> Dict[str, Any]:
        """
        Get the current status of all activities.
        
        Returns:
            Dictionary with activity status information
        """
        now = datetime.now()
        status = {}
        
        for activity_name, config in self.activities_config.items():
            last_executed = self.activity_history.get(activity_name)
            cooldown_seconds = config.get("cooldown", 0)
            
            if last_executed:
                seconds_since = (now - last_executed).total_seconds()
                cooldown_remaining = max(0, cooldown_seconds - seconds_since)
            else:
                seconds_since = None
                cooldown_remaining = 0
                
            enough_energy = self.context.energy >= config.get("min_energy", 0.0)
            
            status[activity_name] = {
                "enabled": config.get("enabled", True),
                "last_executed": last_executed.isoformat() if last_executed else None,
                "seconds_since_last": seconds_since,
                "cooldown_remaining": cooldown_remaining,
                "enough_energy": enough_energy,
                "available": (
                    config.get("enabled", True) and 
                    (not last_executed or seconds_since >= cooldown_seconds) and
                    enough_energy
                )
            }
            
        return status 