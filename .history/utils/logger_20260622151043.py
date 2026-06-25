"""
Logger configuration for Instagram Engagement Scraper.
Provides a pre-configured logger that writes to console and file.
"""

import logging
import os
from pathlib import Path

def get_logger(name: str = "instagram_scraper") -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name, defaults to "instagram_scraper"
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        
        # Console handler - INFO and above
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("[%(levelname)s] %(asctime)s — %(message)s", 
                                              datefmt="%Y-%m-%d %H:%M:%S")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler - DEBUG and above
        file_handler = logging.FileHandler(logs_dir / "scraper.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            "[%(levelname)s] %(asctime)s — %(filename)s:%(lineno)d — %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

