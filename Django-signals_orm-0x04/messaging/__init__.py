# messaging/__init__.py
"""
Messaging application for Django.

This app provides a complete messaging system with:
- User-to-user private messaging
- Group conversations  
- Message notifications via Django signals
- Read status tracking
- Admin interface for message management
"""

# Specify the default app config
default_app_config = 'messaging.apps.MessagingConfig'