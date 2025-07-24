# chats/middleware.py
"""
Basic Request Logging Middleware
Logs each user's requests to a file with timestamp, user, and request path.
"""

import logging
from datetime import datetime, timedelta
import os
from django.conf import settings
from django.http import HttpResponseForbidden
from collections import defaultdict



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


class RestrictAccessByTimeMiddleware:
    """
    Middleware to restrict access to the messaging app during certain hours.
    Denies access outside of 9 PM to 6 PM window (allowing access from 9 PM to 6 PM next day).
    """
    
    def __init__(self, get_response):
        """
        Initialize the middleware.
        
        Args:
            get_response: The next middleware or view in the chain
        """
        self.get_response = get_response
    
    def __call__(self, request):
        """
        Check current server time and restrict access if outside allowed hours.
        
        Args:
            request: The HTTP request object
            
        Returns:
            HttpResponseForbidden if access is denied, otherwise continues to next middleware/view
        """
        # Get current server time
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # Check if current time is outside the allowed window
        # Allowed: 9 PM (21:00) to 6 PM (18:00) next day
        # Denied: 6 PM (18:00) to 9 PM (21:00) same day
        if 18 <= current_hour < 21:  # Between 6 PM and 9 PM (exclusive)
            return HttpResponseForbidden(
                "Access to messaging is restricted during these hours. "
                "Please try again between 9 PM and 6 PM."
            )
        
        # Continue to the next middleware or view
        response = self.get_response(request)
        
        return response
    

class OffensiveLanguageMiddleware:
    """
    Middleware to limit the number of chat messages a user can send within a time window.
    Implements a rate limit of 5 messages per minute per IP address.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        # Dictionary to store request counts and timestamps per IP
        self.request_counts = defaultdict(list)
        # Rate limit configuration
        self.limit = 5  # 5 messages
        self.window = timedelta(minutes=1)  # per minute
    
    def __call__(self, request):
        # Only process POST requests (assuming chat messages are sent via POST)
        if request.method == 'POST':
            ip_address = self.get_client_ip(request)
            current_time = datetime.now()
            
            # Remove timestamps older than our time window
            self.request_counts[ip_address] = [
                timestamp for timestamp in self.request_counts[ip_address]
                if current_time - timestamp < self.window
            ]
            
            # Check if the user has exceeded the limit
            if len(self.request_counts[ip_address]) >= self.limit:
                return HttpResponseForbidden(
                    "You have exceeded the maximum allowed messages (5 per minute). "
                    "Please wait before sending more messages."
                )
            
            # Add the current request timestamp
            self.request_counts[ip_address].append(current_time)
        
        return self.get_response(request)
    
    def get_client_ip(self, request):
        """
        Get the client's IP address from the request object.
        Handles cases where the server is behind a proxy.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip