"""Centralized logging configuration for all services."""
import logging
import sys
from datetime import datetime
from typing import Any, Optional
import json


class ServiceLogger:
    """Enhanced logger for microservices with structured logging."""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create formatter with structured output
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # File handler
        file_handler = logging.FileHandler(f'logs/{service_name}.log')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
        
        # In-memory log buffer for dashboard (last 100 entries)
        self.log_buffer = []
        self.max_buffer_size = 100
    
    def _add_to_buffer(self, level: str, message: str, extra: Optional[dict] = None):
        """Add log entry to in-memory buffer."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "service": self.service_name,
            "message": message,
            "extra": extra or {}
        }
        self.log_buffer.append(entry)
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer.pop(0)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(message)
        self._add_to_buffer("DEBUG", message, kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(message)
        self._add_to_buffer("INFO", message, kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(message)
        self._add_to_buffer("WARNING", message, kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(message)
        self._add_to_buffer("ERROR", message, kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(message)
        self._add_to_buffer("CRITICAL", message, kwargs)
    
    def get_recent_logs(self, limit: int = 50):
        """Get recent log entries for dashboard."""
        return self.log_buffer[-limit:]
    
    def clear_logs(self):
        """Clear the log buffer."""
        self.log_buffer = []
