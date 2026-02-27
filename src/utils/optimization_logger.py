"""
Optimization Logger Module

Provides logging functionality for optimization processes.
Logs to both console and file for tracking optimization performance and results.
"""

import datetime
from pathlib import Path


class OptimizationLogger:
    """Logger for optimization processes that writes to both console and file"""
    
    def __init__(self, log_dir="logs", prefix="optimization"):
        """
        Initialize logger
        
        Args:
            log_dir: Directory to store log files (default: "logs")
            prefix: Prefix for log filenames (default: "optimization")
        """
        self.log_dir = Path(log_dir)
        self.prefix = prefix
        self.log_file = None
        self.log_filename = None
        
    def setup(self):
        """Setup logging to file in logs/ directory"""
        # Create logs directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)
        
        # Create log filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = self.log_dir / f"{self.prefix}_{timestamp}.txt"
        
        # Open log file
        self.log_file = open(self.log_filename, 'w', encoding='utf-8')
        
        print(f"📝 Logging to: {self.log_filename}")
        return self.log_filename
    
    def log(self, message):
        """
        Log message to both console and file
        
        Args:
            message: Message to log
        """
        print(message)  # Console output
        if self.log_file:
            self.log_file.write(message + '\n')
            self.log_file.flush()  # Ensure immediate write
    
    def log_separator(self, char="=", length=70):
        """Log a separator line"""
        self.log(char * length)
    
    def log_section(self, title, char="=", length=70):
        """Log a section header"""
        self.log("")
        self.log_separator(char, length)
        self.log(title)
        self.log_separator(char, length)
    
    def log_timestamp(self, label="Time"):
        """Log current timestamp"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log(f"🕐 {label}: {timestamp}")
    
    def log_duration(self, seconds, label="Duration"):
        """Log duration in seconds and minutes"""
        minutes = seconds / 60
        self.log(f"⏱️  {label}: {seconds:.2f} seconds ({minutes:.2f} minutes)")
    
    def log_summary(self, **kwargs):
        """
        Log optimization summary with key metrics
        
        Args:
            **kwargs: Key-value pairs to log (e.g., total_time=50.12, cost=5595.83)
        """
        self.log_section("🎉 OPTIMIZATION SUMMARY")
        for key, value in kwargs.items():
            # Format key: replace underscores with spaces and capitalize
            formatted_key = key.replace('_', ' ').title()
            
            # Format value based on type
            if isinstance(value, float):
                if 'time' in key.lower() or 'duration' in key.lower():
                    self.log(f"⏱️  {formatted_key}: {value:.2f} seconds ({value/60:.2f} minutes)")
                else:
                    self.log(f"📊 {formatted_key}: {value:.2f}")
            elif isinstance(value, int):
                self.log(f"📊 {formatted_key}: {value:,}")
            else:
                self.log(f"📊 {formatted_key}: {value}")
        
        self.log(f"📝 Log saved to: {self.log_filename}")
        self.log_separator()
    
    def log_error(self, error, elapsed_time=None):
        """
        Log error information
        
        Args:
            error: Exception or error message
            elapsed_time: Optional elapsed time before error
        """
        self.log_section("❌ OPTIMIZATION FAILED")
        self.log_timestamp("Failed at")
        if elapsed_time:
            self.log_duration(elapsed_time, "Time elapsed")
        self.log(f"❌ Error: {str(error)}")
        self.log_separator()
    
    def close(self):
        """Close log file"""
        if self.log_file:
            self.log_file.close()
            self.log_file = None
    
    def __enter__(self):
        """Context manager entry"""
        self.setup()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        return False  # Don't suppress exceptions

