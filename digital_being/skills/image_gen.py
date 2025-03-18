"""Image generation skill using OpenAI DALL-E."""

import logging
import os
from typing import Dict, Any, Tuple, Optional
import random
import asyncio
from pathlib import Path
from openai import OpenAI

logger = logging.getLogger(__name__)

class ImageGenSkill:
    """Skill for generating images using OpenAI's DALL-E."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the image generation skill with configuration from character.json."""
        self.config = config
        self.enabled = config.get("enabled", True)
        self.max_generations = config.get("max_generations_per_day", 10)
        self.supported_formats = config.get("supported_formats", ["png", "jpg"])
        self.supported_sizes = config.get("supported_sizes", ["1024x1024", "512x512"])
        self.generations_count = 0
        
        # Get API key from environment
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables")
            
        # Create storage directory if it doesn't exist
        current_file = Path(__file__)
        project_root = current_file.parent.parent
        self.storage_path = project_root / "storage" / "images"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Image generation storage path: {self.storage_path}")
        
    async def can_generate(self) -> bool:
        """Check if image generation is allowed based on limits and configuration."""
        if not self.enabled:
            logger.warning("Image generation is disabled in character config")
            return False
            
        if self.generations_count >= self.max_generations:
            logger.warning(f"Daily generation limit reached ({self.max_generations})")
            return False
            
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return False
            
        return True
        
    async def generate_image(
        self, 
        prompt: str, 
        size: Tuple[int, int] = (1024, 1024), 
        character_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate an image based on the prompt, incorporating character personality traits.
        
        Args:
            prompt: The base image description
            size: Image dimensions (width, height)
            character_config: Optional character configuration to personalize the image
            
        Returns:
            Dictionary with generation results
        """
        if not await self.can_generate():
            error_msg = "Image generation is not available (disabled, limit reached, or not configured)"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Format the size for OpenAI API
            size_str = f"{size[0]}x{size[1]}"
            if size_str not in self.supported_sizes:
                logger.warning(f"Size {size_str} not in supported sizes, using 1024x1024")
                size_str = "1024x1024"
                
            # Enhance prompt with character personality if provided
            enhanced_prompt = prompt
            if character_config:
                personality = character_config.get("personality", {})
                preferences = character_config.get("preferences", {})
                appearance = character_config.get("appearance", {})
                
                # Extract relevant traits
                creative = personality.get("creativity", 0.5) > 0.6
                analytical = personality.get("analytical", 0.5) > 0.6
                quirky = personality.get("quirkiness", 0.5) > 0.6
                style = preferences.get("writing_style", "")
                color_scheme = appearance.get("color_scheme", "")
                
                # Only enhance if we have meaningful traits
                if any([creative, analytical, quirky]) or style or color_scheme:
                    style_elements = []
                    
                    if creative:
                        style_elements.append("creative and artistic")
                    if analytical:
                        style_elements.append("detailed and precise")
                    if quirky:
                        style_elements.append("unique and slightly unusual")
                    if style:
                        style_elements.append(f"in a {style} style")
                    if color_scheme:
                        style_elements.append(f"with {color_scheme} colors")
                        
                    style_str = ", ".join(style_elements)
                    enhanced_prompt = f"{prompt} The image should be {style_str}."
                    
            logger.info(f"Generating image with prompt: '{enhanced_prompt[:50]}...'")
            
            # Initialize OpenAI client 
            client = OpenAI(api_key=self.api_key)
            
            # Run OpenAI API call in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.images.generate(
                    model="dall-e-3",
                    prompt=enhanced_prompt,
                    n=1,
                    size=size_str,
                    quality="standard",
                    response_format="url",
                )
            )
            
            # Extract the image URL
            image_url = response.data[0].url
            
            # Increment generation counter
            self.generations_count += 1
            
            # Get revised prompt that DALL-E actually used (if available)
            revised_prompt = getattr(response.data[0], "revised_prompt", enhanced_prompt)
            
            # Generate an ID for this image
            generation_id = f"image_{self.generations_count}_{random.randint(1000, 9999)}"
            
            # Return the result
            return {
                "success": True,
                "image_data": {
                    "url": image_url,
                    "width": size[0],
                    "height": size[1],
                    "generation_id": generation_id,
                },
                "metadata": {
                    "original_prompt": prompt,
                    "enhanced_prompt": enhanced_prompt,
                    "revised_prompt": revised_prompt,
                    "generation_number": self.generations_count,
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate image: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
            
    def reset_counts(self):
        """Reset the generation counter (e.g., at the start of a new day)."""
        self.generations_count = 0