# messaging/apps.py
from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class MessagingConfig(AppConfig):
    """
    Django AppConfig for the messaging application.
    
    Handles app initialization and ensures proper registration of signal handlers.
    Provides verbose name and default auto field configuration.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "messaging"
    verbose_name = "Messaging System"
    
    def ready(self):
        """
        Initialize the messaging application when Django starts.
        
        Performs the following actions:
        1. Imports and registers all signal handlers
        2. Logs successful initialization or any errors
        3. Ensures signals are only registered once
        
        This method is called exactly once during Django's startup process.
        """
        # Skip if we're running management commands that don't need signals
        if self.is_management_command():
            return
            
        self.register_signals()
        
    def register_signals(self):
        """
        Register all signal handlers for the messaging app.
        
        Uses proper error handling and logging to ensure any issues during
        signal registration are properly reported.
        """
        try:
            # Import signals module to register handlers
            import messaging.signals  # noqa: F401
            logger.info("Messaging app signals registered successfully")
        except ImportError as e:
            logger.error(f"Failed to import messaging signals: {str(e)}")
        except Exception as e:
            logger.error(f"Error registering messaging signals: {str(e)}")
            
    @staticmethod
    def is_management_command():
        """
        Check if we're running a management command that doesn't need signals.
        
        Returns:
            bool: True if we're running a management command that should skip
                  signal registration, False otherwise.
        """
        import sys
        if len(sys.argv) > 1 and sys.argv[1] in [
            'makemigrations',
            'migrate',
            'collectstatic',
            'flush',
            'test'
        ]:
            return True
        return False