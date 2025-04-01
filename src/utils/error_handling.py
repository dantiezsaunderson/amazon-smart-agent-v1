"""
Logging and error handling module for Amazon Smart Agent
Provides centralized logging configuration and error handling utilities
"""

import os
import sys
import logging
import traceback
import json
from datetime import datetime
from typing import Dict, Any, Optional, Callable, Union
import functools
import time
import random

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

class LoggingManager:
    """Manages logging configuration for the application"""
    
    def __init__(self, log_dir: str = None, log_level: str = 'INFO'):
        """
        Initialize logging manager
        
        Args:
            log_dir: Directory to store log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Initialize loggers dictionary
        self.loggers = {}
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create a logger with the specified name
        
        Args:
            name: Logger name
            
        Returns:
            Configured logger
        """
        if name in self.loggers:
            return self.loggers[name]
        
        # Create new logger
        logger = logging.getLogger(name)
        logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create file handler
        log_file = os.path.join(self.log_dir, f"{name.replace('.', '_')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(self.log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        logger.addHandler(file_handler)
        
        # Store logger
        self.loggers[name] = logger
        
        return logger
    
    def configure_global_logging(self):
        """Configure global logging settings"""
        # Create main log file handler
        main_log_file = os.path.join(self.log_dir, 'amazon_smart_agent.log')
        file_handler = logging.FileHandler(main_log_file)
        file_handler.setLevel(self.log_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        root_logger.addHandler(file_handler)
        
        # Create error log file handler
        error_log_file = os.path.join(self.log_dir, 'errors.log')
        error_file_handler = logging.FileHandler(error_log_file)
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        
        # Add error handler to root logger
        root_logger.addHandler(error_file_handler)
        
        logger.info(f"Global logging configured. Log files in: {self.log_dir}")
    
    def log_to_file(self, message: str, level: str = 'INFO', log_file: str = None):
        """
        Log a message to a specific file
        
        Args:
            message: Message to log
            level: Log level
            log_file: Log file name (without path)
        """
        if not log_file:
            log_file = 'custom.log'
        
        file_path = os.path.join(self.log_dir, log_file)
        
        # Get numeric level
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(file_path)
        file_handler.setLevel(numeric_level)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Create logger
        custom_logger = logging.getLogger(f"custom.{log_file}")
        custom_logger.setLevel(numeric_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in custom_logger.handlers[:]:
            custom_logger.removeHandler(handler)
        
        # Add handler
        custom_logger.addHandler(file_handler)
        
        # Log message
        log_method = getattr(custom_logger, level.lower(), custom_logger.info)
        log_method(message)
        
        # Remove handler
        custom_logger.removeHandler(file_handler)
        file_handler.close()


class ErrorHandler:
    """Handles errors and exceptions in the application"""
    
    def __init__(self, log_dir: str = None):
        """
        Initialize error handler
        
        Args:
            log_dir: Directory to store error logs
        """
        self.log_dir = log_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        
        # Create log directory if it doesn't exist
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create error logger
        self.error_logger = logging.getLogger('error_handler')
        self.error_logger.setLevel(logging.ERROR)
        
        # Remove existing handlers to avoid duplicates
        for handler in self.error_logger.handlers[:]:
            self.error_logger.removeHandler(handler)
        
        # Create file handler
        error_log_file = os.path.join(self.log_dir, 'errors.log')
        file_handler = logging.FileHandler(error_log_file)
        file_handler.setLevel(logging.ERROR)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        self.error_logger.addHandler(file_handler)
    
    def handle_exception(self, exc_type, exc_value, exc_traceback):
        """
        Global exception handler for unhandled exceptions
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the exception
        self.error_logger.error(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # Log to error file with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        error_detail_file = os.path.join(self.log_dir, f'error_detail_{timestamp}.log')
        
        with open(error_detail_file, 'w') as f:
            f.write(f"Exception occurred at: {datetime.now().isoformat()}\n")
            f.write(f"Type: {exc_type.__name__}\n")
            f.write(f"Value: {exc_value}\n")
            f.write("\nTraceback:\n")
            traceback.print_tb(exc_traceback, file=f)
            f.write("\nFull traceback:\n")
            traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        
        # Print to stderr
        print(f"An error occurred: {exc_value}", file=sys.stderr)
        print(f"Error details saved to: {error_detail_file}", file=sys.stderr)
    
    def install_global_handler(self):
        """Install global exception handler"""
        sys.excepthook = self.handle_exception
        logger.info("Global exception handler installed")
    
    def log_error(self, error: Exception, context: str = None):
        """
        Log an error with context
        
        Args:
            error: Exception to log
            context: Context information
        """
        if context:
            self.error_logger.error(f"{context}: {str(error)}", exc_info=error)
        else:
            self.error_logger.error(str(error), exc_info=error)
    
    def create_error_report(self, error: Exception, context: Dict[str, Any] = None) -> str:
        """
        Create detailed error report
        
        Args:
            error: Exception to report
            context: Context information
            
        Returns:
            Path to error report file
        """
        # Create report with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.log_dir, f'error_report_{timestamp}.json')
        
        # Gather error information
        error_info = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error.__class__.__name__,
            'error_message': str(error),
            'traceback': traceback.format_exc(),
        }
        
        # Add context if provided
        if context:
            error_info['context'] = context
        
        # Add system information
        error_info['system_info'] = {
            'python_version': sys.version,
            'platform': sys.platform,
            'executable': sys.executable,
        }
        
        # Write report to file
        with open(report_file, 'w') as f:
            json.dump(error_info, f, indent=2)
        
        self.error_logger.error(f"Error report created: {report_file}")
        return report_file


# Retry decorator
def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0, 
          exceptions: tuple = (Exception,), logger: logging.Logger = None):
    """
    Retry decorator with exponential backoff
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier
        exceptions: Exceptions to catch and retry
        logger: Logger to use for logging retries
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            local_logger = logger or logging.getLogger(func.__module__)
            
            attempt = 1
            current_delay = delay
            
            while attempt <= max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        local_logger.error(f"Failed after {max_attempts} attempts: {str(e)}")
                        raise
                    
                    local_logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {str(e)}. "
                        f"Retrying in {current_delay:.2f} seconds..."
                    )
                    
                    # Add jitter to avoid thundering herd
                    jitter = random.uniform(0, 0.1 * current_delay)
                    time.sleep(current_delay + jitter)
                    
                    # Increase delay for next attempt
                    current_delay *= backoff
                    attempt += 1
        
        return wrapper
    
    return decorator


# Function to initialize logging and error handling
def initialize_error_handling():
    """Initialize logging and error handling for the application"""
    # Create logging manager
    logging_manager = LoggingManager()
    logging_manager.configure_global_logging()
    
    # Create error handler
    error_handler = ErrorHandler()
    error_handler.install_global_handler()
    
    return logging_manager, error_handler
