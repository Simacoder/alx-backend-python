# messaging/apps.py
from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """
    Django app configuration for the messaging application.
    
    This configuration class handles the initialization of the messaging app
    and ensures that signal handlers are properly registered.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "messaging"
    verbose_name = "Messaging System"
    
    def ready(self):
        """
        This method is called when Django starts up.
        
        It's the perfect place to import and register signal handlers
        to ensure they are connected when the application starts.
        """
        try:
            # Import signal handlers to register them
            import messaging.signals
            print("Messaging app signals registered successfully")
        except ImportError as e:
            print(f"Error importing messaging signals: {e}")
        
        