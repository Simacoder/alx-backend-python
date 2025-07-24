# chats/middleware.py
"""
Basic Request Logging Middleware
Logs each user's requests to a file with timestamp, user, and request path.
"""

import logging
from datetime import datetime
import os
from django.conf import settings


class RequestLoggingMiddleware:
    """
    Middleware to log user requests to a file.
    Logs timestamp, user, and request path for each request.
    """
    
    def __init__(self, get_response):
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
        
        # Set up logging configuration
        self.setup_logging()
    
    def setup_logging(self):
        """Configure logging to write to requests.log file"""
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(settings.BASE_DIR, '')  # Root directory
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure logger
        self.logger = logging.getLogger('request_logger')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler if it doesn't exist
        if not self.logger.handlers:
            log_file = os.path.join(logs_dir, 'requests.log')
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            # Create formatter - simple format to match requirements
            formatter = logging.Formatter('%(message)s')
            file_handler.setFormatter(formatter)
            
            # Add handler to logger
            self.logger.addHandler(file_handler)
    
    def __call__(self, request):
        """
        Process the request and log the required information.
        
        Args:
            request: The HTTP request object
            
        Returns:
            The response from the next middleware or view
        """
        # Get user information
        if hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user.username
        else:
            user = "Anonymous"
        
        # Create log message with required format
        log_message = f"{datetime.now()} - User: {user} - Path: {request.path}"
        
        # Log the request information
        self.logger.info(log_message)
        
        # Continue to the next middleware or view
        response = self.get_response(request)
        
        return response