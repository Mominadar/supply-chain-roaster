"""
Configuration Logger - Professional logging utility for configuration management

This module provides clean, structured logging for configuration values across the application.
Supports multiple configuration types and sources with consistent formatting.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from enum import Enum


class ConfigSource(Enum):
    """Configuration source types"""
    SESSION_STATE = "SESSION_STATE"
    DEFAULT = "DEFAULT"
    FILE = "FILE"
    DATABASE = "DATABASE"
    ENVIRONMENT = "ENVIRONMENT"


class ConfigLogger:
    """
    Professional configuration logger with structured output.
    
    Provides clean, consistent logging for configuration values with:
    - Multiple source tracking
    - Missing field detection
    - Pretty formatting
    - Type-aware value display
    """
    
    # Icons for different sources
    SOURCE_ICONS = {
        ConfigSource.SESSION_STATE: "📅",
        ConfigSource.DEFAULT: "🔧",
        ConfigSource.FILE: "📄",
        ConfigSource.DATABASE: "💾",
        ConfigSource.ENVIRONMENT: "🌍"
    }
    
    def __init__(self, name: str = "ConfigLogger", level: int = logging.INFO):
        """
        Initialize configuration logger.
        
        Args:
            name: Logger name
            level: Logging level (default: INFO)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setLevel(level)
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _format_value(self, value: Any) -> str:
        """
        Format value for display with type awareness.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted string representation
        """
        if isinstance(value, (datetime, date)):
            return str(value.date() if hasattr(value, 'date') else value)
        elif isinstance(value, list):
            if len(value) > 10:
                return f"[{', '.join(map(str, value[:5]))}, ... ({len(value)} items)]"
            return str(value)
        elif isinstance(value, dict):
            if len(value) > 5:
                items = list(value.items())[:3]
                preview = ', '.join(f"{k}: {v}" for k, v in items)
                return f"{{{preview}, ... ({len(value)} items)}}"
            return str(value)
        else:
            return str(value)
    
    def log_config(
        self,
        config_name: str,
        source: Union[ConfigSource, str],
        values: Dict[str, Any],
        missing_fields: Optional[List[str]] = None,
        warning_message: Optional[str] = None
    ) -> None:
        """
        Log configuration values with clean formatting.
        
        Args:
            config_name: Name of the configuration (e.g., "Date Configuration")
            source: Configuration source
            values: Dictionary of configuration key-value pairs
            missing_fields: List of missing field names (optional)
            warning_message: Additional warning message (optional)
        
        Example:
            >>> logger.log_config(
            ...     "Date Configuration",
            ...     ConfigSource.SESSION_STATE,
            ...     {"start_date": datetime(2025, 7, 7), "planning_days": 5}
            ... )
        """
        # Convert string to enum if needed
        if isinstance(source, str):
            try:
                source = ConfigSource[source]
            except KeyError:
                source = ConfigSource.DEFAULT
        
        # Log missing fields warning
        if missing_fields:
            self.logger.warning(
                f"⚠️  [{config_name.upper()}] Session state missing: {', '.join(missing_fields)}"
            )
        
        # Log custom warning message
        if warning_message:
            self.logger.warning(f"⚠️  [{config_name.upper()}] {warning_message}")
        
        # Get icon for source
        icon = self.SOURCE_ICONS.get(source, "🔹")
        
        # Log header
        self.logger.info(f"{icon} [{config_name.upper()}] Using values from {source.value}:")
        
        # Log each configuration value
        for key, value in values.items():
            formatted_value = self._format_value(value)
            self.logger.info(f"   • {key}: {formatted_value}")
    
    def log_date_config(
        self,
        source: Union[ConfigSource, str],
        start_date: Any,
        end_date: Any,
        planning_days: int,
        date_span: List[int],
        missing_fields: Optional[List[str]] = None
    ) -> None:
        """
        Convenience method for logging date configuration.
        
        Args:
            source: Configuration source
            start_date: Start date
            end_date: End date
            planning_days: Number of planning days
            date_span: List of day numbers
            missing_fields: List of missing field names (optional)
        """
        self.log_config(
            config_name="Date Config",
            source=source,
            values={
                "Start Date": start_date,
                "End Date": end_date,
                "Planning Days": planning_days,
                "Date Span": date_span
            },
            missing_fields=missing_fields
        )
    
    def log_employee_config(
        self,
        source: Union[ConfigSource, str],
        employee_types: List[str],
        max_per_day: Dict[str, int],
        missing_fields: Optional[List[str]] = None
    ) -> None:
        """
        Convenience method for logging employee configuration.
        
        Args:
            source: Configuration source
            employee_types: List of employee types
            max_per_day: Dictionary of max employees per day
            missing_fields: List of missing field names (optional)
        """
        self.log_config(
            config_name="Employee Config",
            source=source,
            values={
                "Employee Types": employee_types,
                "Max Per Day": max_per_day
            },
            missing_fields=missing_fields
        )
    
    def log_line_config(
        self,
        source: Union[ConfigSource, str],
        line_types: List[int],
        line_counts: Dict[int, int],
        max_parallel_workers: Dict[int, int],
        missing_fields: Optional[List[str]] = None
    ) -> None:
        """
        Convenience method for logging line configuration.
        
        Args:
            source: Configuration source
            line_types: List of line type IDs
            line_counts: Dictionary of line counts per type
            max_parallel_workers: Dictionary of max parallel workers per type
            missing_fields: List of missing field names (optional)
        """
        self.log_config(
            config_name="Line Config",
            source=source,
            values={
                "Line Types": line_types,
                "Line Counts": line_counts,
                "Max Parallel Workers": max_parallel_workers
            },
            missing_fields=missing_fields
        )


# Global logger instance for easy import
config_logger = ConfigLogger(name="SD_Roster_Config")


def log_config(
    config_name: str,
    source: Union[ConfigSource, str],
    values: Dict[str, Any],
    missing_fields: Optional[List[str]] = None,
    warning_message: Optional[str] = None
) -> None:
    """
    Quick function to log configuration using global logger.
    
    Args:
        config_name: Name of the configuration
        source: Configuration source
        values: Dictionary of configuration key-value pairs
        missing_fields: List of missing field names (optional)
        warning_message: Additional warning message (optional)
    """
    config_logger.log_config(config_name, source, values, missing_fields, warning_message)

