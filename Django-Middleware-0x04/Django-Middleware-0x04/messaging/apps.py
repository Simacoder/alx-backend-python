from django.apps import AppConfig


class MessagingConfig(AppConfig):
    """
    Configuration for the messaging app.
    This class handles app initialization and ensures signals are properly connected.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging'
    verbose_name = 'Messaging System'

    def ready(self):
        """
        Method called when Django starts up.
        This is where we import and register our signals.
        """
        try:
            # Import signals to ensure they are registered
            import messaging.signals
            print("Messaging signals loaded successfully")
        except ImportError as e:
            print(f"Error importing messaging signals: {e}")
        except Exception as e:
            print(f"Unexpected error loading messaging signals: {e}")