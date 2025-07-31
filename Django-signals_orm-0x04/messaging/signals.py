# messaging/signals.py
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Message, Notification, Conversation

User = get_user_model()


@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Signal handler to create notifications when a new message is created.
    
    This signal is triggered after a Message instance is saved.
    It creates notifications for all conversation participants except the sender.
    """
    if created:  # Only for new messages, not updates
        message = instance
        conversation = message.conversation
        sender_user = message.sender
        
        # Get all participants except the sender
        recipients = conversation.participants.exclude(user_id=sender_user.user_id)
        
        # Create notifications for each recipient
        notifications_to_create = []
        
        for recipient in recipients:
            # Generate notification title and content
            if conversation.is_group:
                title = f"New message in {conversation.title or 'group chat'}"
                content = f"{sender_user.get_full_name()} sent: {message.message_body[:100]}..."
            else:
                title = f"New message from {sender_user.get_full_name()}"
                content = message.message_body[:200] + ("..." if len(message.message_body) > 200 else "")
            
            # Create notification object (but don't save yet for bulk creation)
            notification = Notification(
                recipient=recipient,
                sender=sender_user,
                message=message,
                conversation=conversation,
                notification_type='message',
                title=title,
                content=content,
                is_sent=False,  # Will be marked as sent by notification service
            )
            notifications_to_create.append(notification)
        
        # Bulk create notifications for better performance
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)
            
            #  Log the notification creation
            print(f"Created {len(notifications_to_create)} notifications for message {message.message_id}")


@receiver(m2m_changed, sender=Conversation.participants.through)
def create_group_notification(sender, instance, action, pk_set, **kwargs):
    """
    Signal handler to create notifications when users are added/removed from conversations.
    
    This signal is triggered when the many-to-many relationship between
    Conversation and User (participants) is changed.
    """
    if action == "post_add" and pk_set:
        # Users were added to the conversation
        conversation = instance
        added_users = User.objects.filter(pk__in=pk_set)
        
        for added_user in added_users:
            # Create notification for the added user
            if conversation.is_group:
                title = f"Added to group chat"
                content = f"You were added to '{conversation.title or 'a group chat'}'"
                
                # Also notify existing participants (except the added user)
                existing_participants = conversation.participants.exclude(pk=added_user.pk)
                
                # Notification for the added user
                Notification.objects.create(
                    recipient=added_user,
                    sender=conversation.created_by,  # Assuming group creator added them
                    conversation=conversation,
                    notification_type='group_add',
                    title=title,
                    content=content,
                )
                
                # Notify existing participants about the new member
                for participant in existing_participants:
                    Notification.objects.create(
                        recipient=participant,
                        sender=conversation.created_by,
                        conversation=conversation,
                        notification_type='group_add',
                        title=f"New member added",
                        content=f"{added_user.get_full_name()} was added to the group",
                    )
    
    elif action == "post_remove" and pk_set:
        # Users were removed from the conversation
        conversation = instance
        removed_users = User.objects.filter(pk__in=pk_set)
        
        for removed_user in removed_users:
            # Create notification for the removed user
            if conversation.is_group:
                Notification.objects.create(
                    recipient=removed_user,
                    sender=conversation.created_by,
                    conversation=conversation,
                    notification_type='group_remove',
                    title=f"Removed from group chat",
                    content=f"You were removed from '{conversation.title or 'a group chat'}'",
                )
                
                # Notify remaining participants
                remaining_participants = conversation.participants.all()
                for participant in remaining_participants:
                    Notification.objects.create(
                        recipient=participant,
                        sender=conversation.created_by,
                        conversation=conversation,
                        notification_type='group_remove',
                        title=f"Member removed",
                        content=f"{removed_user.get_full_name()} was removed from the group",
                    )


@receiver(post_save, sender=Notification)
def log_notification_creation(sender, instance, created, **kwargs):
    """
    Optional signal handler to log when notifications are created.
    
    This can be useful for debugging and monitoring notification creation.
    """
    if created:
        print(f"New notification created: {instance.notification_type} for {instance.recipient.username}")
        
        # Here you could add additional logic like:
        # - Sending push notifications
        # - Sending emails
        # - Updating real-time notification counts
        # - Integration with external notification services


# Additional helper functions for notification management

def mark_conversation_notifications_as_read(user, conversation):
    """
    Mark all notifications for a specific conversation as read for a user.
    
    This function can be called when a user opens a conversation.
    """
    notifications = Notification.objects.filter(
        recipient=user,
        conversation=conversation,
        is_read=False
    )
    
    notifications.update(is_read=True, read_at=models.DateTimeField(auto_now=True))
    return notifications.count()


def get_unread_notification_count(user):
    """
    Get the count of unread notifications for a user.
    
    This can be used to display notification badges in the UI.
    """
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_recent_notifications(user, limit=20):
    """
    Get recent notifications for a user.
    
    Args:
        user: The user to get notifications for
        limit: Maximum number of notifications to return
    
    Returns:
        QuerySet of recent notifications
    """
    return Notification.objects.filter(
        recipient=user
    ).select_related(
        'sender', 'message', 'conversation'
    ).order_by('-created_at')[:limit]