from django.db.models.signals import post_save, m2m_changed, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
import logging
from .models import Message, Notification, Conversation, MessageHistory, MessageReadStatus

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationService:
    """Helper class for notification-related operations"""
    
    @staticmethod
    def create_message_notification(message, recipient, is_group):
        """Create a notification for a new message"""
        if is_group:
            return Notification(
                recipient=recipient,
                sender=message.sender,
                message=message,
                conversation=message.conversation,
                notification_type='message',
                title=f"New message in {message.conversation.title or 'group chat'}",
                content=f"{message.sender.get_full_name()} sent: {message.message_body[:100]}...",
                is_sent=False
            )
        else:
            return Notification(
                recipient=recipient,
                sender=message.sender,
                message=message,
                conversation=message.conversation,
                notification_type='message',
                title=f"New message from {message.sender.get_full_name()}",
                content=message.message_body[:200] + ("..." if len(message.message_body) > 200 else ""),
                is_sent=False
            )


# ====================== Message Signals ======================
@receiver(post_save, sender=Message)
def handle_new_message(sender, instance, created, **kwargs):
    """Handle all post-save operations for Messages"""
    if created:
        try:
            with transaction.atomic():
                create_message_notification(instance)
                update_conversation_timestamp(instance)
        except Exception as e:
            logger.error(f"Error handling new message: {str(e)}")


def create_message_notification(message):
    """Create notifications for a new message"""
    conversation = message.conversation
    recipients = conversation.participants.exclude(user_id=message.sender.user_id)
    
    notifications = [
        NotificationService.create_message_notification(message, recipient, conversation.is_group)
        for recipient in recipients
    ]
    
    if notifications:
        Notification.objects.bulk_create(notifications)
        logger.debug(f"Created {len(notifications)} notifications for message {message.message_id}")


def update_conversation_timestamp(message):
    """Update conversation's last updated timestamp"""
    message.conversation.save(update_fields=['updated_at'])


@receiver(pre_save, sender=Message)
def handle_message_edit(sender, instance, **kwargs):
    """Track message edits by saving previous versions"""
    if not instance.pk:  # Skip new messages
        return

    try:
        old_message = Message.objects.get(pk=instance.pk)
        if old_message.message_body == instance.message_body:
            return

        latest_version = MessageHistory.objects.filter(
            message=instance
        ).order_by('-version').first()
        
        new_version = (latest_version.version + 1) if latest_version else 1
        
        MessageHistory.objects.create(
            message=instance,
            old_content=old_message.message_body,
            new_content=instance.message_body,
            edited_by=instance.sender,
            version=new_version,
        )
        logger.debug(f"Created edit history v{new_version} for message {instance.message_id}")

    except Exception as e:
        logger.error(f"Error logging message edit: {str(e)}")


# ====================== User Deletion Signals ======================
@receiver(post_delete, sender=User)
def clean_up_user_data(sender, instance, **kwargs):
    """
    Comprehensive cleanup of all user-related data.
    Runs in atomic transaction to ensure data consistency.
    """
    try:
        with transaction.atomic():
            # Delete all user-created content
            Message.objects.filter(sender=instance).delete()
            Notification.objects.filter(Q(recipient=instance) | Q(sender=instance)).delete()
            MessageHistory.objects.filter(edited_by=instance).delete()
            MessageReadStatus.objects.filter(user=instance).delete()
            
            # Remove user as conversation creator without deleting conversations
            Conversation.objects.filter(created_by=instance).update(created_by=None)
            
            logger.info(f"Successfully cleaned up data for deleted user {instance.username}")

    except Exception as e:
        logger.error(f"Error cleaning up user {instance.username} data: {str(e)}")
        # Continue despite errors since user is already deleted


# ====================== Conversation Signals ======================
@receiver(m2m_changed, sender=Conversation.participants.through)
def handle_participant_changes(sender, instance, action, pk_set, **kwargs):
    """Manage notifications for group participant changes"""
    if not instance.is_group or not pk_set:
        return

    try:
        if action == "post_add":
            notify_participants_added(instance, pk_set)
        elif action == "post_remove":
            notify_participants_removed(instance, pk_set)
    except Exception as e:
        logger.error(f"Error handling participant changes: {str(e)}")


def notify_participants_added(conversation, user_ids):
    """Notify about new group members"""
    added_users = User.objects.filter(pk__in=user_ids)
    creator = conversation.created_by

    for user in added_users:
        # Notify the new participant
        Notification.objects.create(
            recipient=user,
            sender=creator,
            conversation=conversation,
            notification_type='group_add',
            title="Added to group chat",
            content=f"You were added to '{conversation.title or 'a group chat'}'",
        )

        # Notify existing participants
        existing_participants = conversation.participants.exclude(pk__in=[user.pk, creator.pk])
        for participant in existing_participants:
            Notification.objects.create(
                recipient=participant,
                sender=creator,
                conversation=conversation,
                notification_type='group_add',
                title="New member added",
                content=f"{user.get_full_name()} was added to the group",
            )


def notify_participants_removed(conversation, user_ids):
    """Notify about removed group members"""
    removed_users = User.objects.filter(pk__in=user_ids)
    creator = conversation.created_by

    for user in removed_users:
        # Notify the removed user
        Notification.objects.create(
            recipient=user,
            sender=creator,
            conversation=conversation,
            notification_type='group_remove',
            title="Removed from group chat",
            content=f"You were removed from '{conversation.title or 'a group chat'}'",
        )

        # Notify remaining participants
        remaining_participants = conversation.participants.exclude(pk=user.pk)
        for participant in remaining_participants:
            Notification.objects.create(
                recipient=participant,
                sender=creator,
                conversation=conversation,
                notification_type='group_remove',
                title="Member removed",
                content=f"{user.get_full_name()} was removed from the group",
            )


# ====================== MessageHistory Signals ======================
@receiver(post_save, sender=MessageHistory)
def notify_about_edits(sender, instance, created, **kwargs):
    """Notify participants about message edits"""
    if not created or instance.version <= 1:
        return

    try:
        conversation = instance.message.conversation
        editor = instance.edited_by
        
        recipients = conversation.participants.exclude(pk=editor.pk)
        for recipient in recipients:
            Notification.objects.create(
                recipient=recipient,
                sender=editor,
                message=instance.message,
                conversation=conversation,
                notification_type='message_edit',
                title=f'{editor.get_full_name()} edited a message',
                content=f'Message in "{conversation}" was edited'
            )
    except Exception as e:
        logger.error(f"Error creating edit notifications: {str(e)}")


# ====================== Notification Utilities ======================
def mark_conversation_notifications_as_read(user, conversation):
    """Mark all conversation notifications as read for a user"""
    try:
        updated = Notification.objects.filter(
            recipient=user,
            conversation=conversation,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return updated
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")
        return 0


def get_unread_notification_count(user):
    """Count unread notifications for a user"""
    try:
        return Notification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
    except Exception as e:
        logger.error(f"Error counting unread notifications: {str(e)}")
        return 0


def get_recent_notifications(user, limit=20):
    """Get recent notifications with related objects"""
    try:
        return Notification.objects.filter(
            recipient=user
        ).select_related(
            'sender', 'message', 'conversation'
        ).order_by('-created_at')[:limit]
    except Exception as e:
        logger.error(f"Error fetching notifications: {str(e)}")
        return Notification.objects.none()