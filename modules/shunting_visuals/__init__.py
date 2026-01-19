"""
Shunting Visuals Module
This module handles shunting data visualization and analysis
"""

import logging
import sys

logger = logging.getLogger(__name__)
logger.info("Initializing shunting_visuals module...")

# First, try to import dependencies
try:
    from .load_shunting_visuals_data import ShuntingDataLoader
    logger.info("✓ ShuntingDataLoader class imported in __init__")
except Exception as e:
    logger.error(f"✗ Failed to import ShuntingDataLoader in __init__: {str(e)}", exc_info=True)
    ShuntingDataLoader = None

try:
    from .shunting_visuals_main import ShuntingVisualsProcessor  
    logger.info("✓ ShuntingVisualsProcessor class imported in __init__")
except Exception as e:
    logger.error(f"✗ Failed to import ShuntingVisualsProcessor in __init__: {str(e)}", exc_info=True)
    ShuntingVisualsProcessor = None

# Then import the blueprint
try:
    from .routes_shunting_visuals import shunting_visuals_bp
    logger.info("✓ Shunting Visuals routes blueprint imported successfully")
    __all__ = ['shunting_visuals_bp']
except Exception as e:
    logger.error(f"✗ Failed to import shunting_visuals_bp: {str(e)}", exc_info=True)
    raise