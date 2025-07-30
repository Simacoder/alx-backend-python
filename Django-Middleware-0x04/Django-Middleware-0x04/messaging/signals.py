from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import logging

from .models import Message, Notification

# Set up logging
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal handler that creates a notification when a new message is created.
    
    Args:
        sender: The model class (Message)
        instance: The actual Message instance
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:
        try:
            # Create notification for the message receiver
            notification = Notification.create_message_notification(instance)
            
            # Log the notification creation
            logger.info(
                f"Notification created for user {instance.receiver.username} "
                f"about message from {instance.sender.username}"
            )
            
            # Optional: Send email notification if user has email
            if hasattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED') and settings.EMAIL_NOTIFICATIONS_ENABLED:
                send_email_notification(instance, notification)
                
        except Exception as e:
            logger.error(f"Failed to create notification for message {instance.id}: {str(e)}")


@receiver(post_save, sender=Message)
def log_message_activity(sender, instance, created, **kwargs):
    """
    Signal handler that logs message activity for monitoring purposes.
    
    Args:
        sender: The model class (Message)
        instance: The actual Message instance
        created: Boolean indicating if this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:
        logger.info(
            f"New message created: ID={instance.id}, "
            f"From={instance.sender.username}, "
            f"To={instance.receiver.username}, "
            f"At={instance.timestamp}"
        )
    else:
        logger.info(f"Message updated: ID={instance.id}")


@receiver(post_delete, sender=Message)
def log_message_deletion(sender, instance, **kwargs):
    """
    Signal handler that logs when a message is deleted.
    
    Args:
        sender: The model class (Message)
        instance: The Message instance being deleted
        **kwargs: Additional keyword arguments
    """
    logger.info(f"Message deleted: ID={instance.id}")


@receiver(pre_save, sender=Message)
def prevent_self_messaging(sender, instance, **kwargs):
    """
    Signal handler that prevents users from sending messages to themselves.
    
    Args:
        sender: The model class (Message)
        instance: The Message instance being saved
        **kwargs: Additional keyword arguments
    """
    if instance.sender == instance.receiver:
        raise ValueError("Users cannot send messages to themselves")


def send_email_notification(message, notification):
    """
    Send an email notification for a new message.
    
    Args:
        message (Message): The message instance
        notification (Notification): The notification instance
    """
    try:
        if message.receiver.email:
            subject = f"New message from {message.sender.username}"
            message_body = f"""
            Hi {message.receiver.username},
            
            You have received a new message from {message.sender.username}:
            
            "{message.content}"
            
            You can view and reply to this message by logging into your account.
            
            Best regards,
            The Team
            """
            
            send_mail(
                subject=subject,
                message=message_body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[message.receiver.email],
                fail_silently=True
            )
            
            logger.info(f"Email notification sent to {message.receiver.email}")
            
    except Exception as e:
        logger.error(f"Failed to send email notification: {str(e)}")


# Additional utility signal handlers for notification management

@receiver(post_save, sender=Notification)
def log_notification_creation(sender, instance, created, **kwargs):
    """
    Signal handler that logs when notifications are created.
    """
    if created:
        logger.info(
            f"Notification created: ID={instance.id}, "
            f"User={instance.user.username}, "
            f"Type={instance.notification_type}"
        )


@receiver(post_delete, sender=Notification)
def log_notification_deletion(sender, instance, **kwargs):
    """
    Signal handler that logs when notifications are deleted.
    """
    logger.info(f"Notification deleted: ID={instance.id}")


# Signal for user profile updates (bonus feature)
@receiver(post_save, sender=User)
def log_user_activity(sender, instance, created, **kwargs):
    """
    Signal handler that logs user activity.
    """
    if created:
        logger.info(f"New user created: {instance.username}")
    else:
        logger.info(f"User updated: {instance.username}")


# Clean up notifications when messages are deleted
@receiver(post_delete, sender=Message)
def cleanup_message_notifications(sender, instance, **kwargs):
    """
    Signal handler that cleans up related notifications when a message is deleted.
    """
    try:
        # Delete all notifications related to this message
        deleted_count = Notification.objects.filter(message=instance).delete()[0]
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} notifications for deleted message {instance.id}")
    except Exception as e:
        logger.error(f"Failed to cleanup notifications for message {instance.id}: {str(e)}")