#!/usr/bin/env python3
"""
Logging utilities for TV Show Organizer
Provides colored console logging and file logging capabilities.
"""

import logging
from pathlib import Path
from typing import Optional


# ANSI color codes for terminal output
class Colors:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels"""
    COLORS = {
        'DEBUG': Colors.BLUE,
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'CRITICAL': Colors.RED + Colors.BOLD
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, Colors.RESET)
        record.levelname = f"{color}{record.levelname}{Colors.RESET}"
        return super().format(record)


def setup_logging(log_file: Path, verbose: bool = False) -> logging.Logger:
    """
    Setup colored logging with file handler
    
    Args:
        log_file: Path to the log file
        verbose: If True, enable DEBUG level logging
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('TVOrganizer')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler with colored output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    console_formatter = ColoredFormatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with detailed formatting (no ANSI colors)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

