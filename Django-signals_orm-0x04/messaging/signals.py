# messaging/signals.py
from django.db.models.signals import post_save, m2m_changed, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Message, Notification, Conversation, MessageHistory

User = get_user_model()


# ====================== Message Signals ======================
@receiver(post_save, sender=Message)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Create notifications when a new message is created.
    Notifications are created for all conversation participants except the sender.
    """
    if created:
        message = instance
        conversation = message.conversation
        sender_user = message.sender
        
        recipients = conversation.participants.exclude(user_id=sender_user.user_id)
        notifications_to_create = []
        
        for recipient in recipients:
            if conversation.is_group:
                title = f"New message in {conversation.title or 'group chat'}"
                content = f"{sender_user.get_full_name()} sent: {message.message_body[:100]}..."
            else:
                title = f"New message from {sender_user.get_full_name()}"
                content = message.message_body[:200] + ("..." if len(message.message_body) > 200 else "")
            
            notifications_to_create.append(Notification(
                recipient=recipient,
                sender=sender_user,
                message=message,
                conversation=conversation,
                notification_type='message',
                title=title,
                content=content,
                is_sent=False,
            ))
        
        if notifications_to_create:
            Notification.objects.bulk_create(notifications_to_create)
            print(f"Created {len(notifications_to_create)} notifications for message {message.message_id}")


@receiver(pre_save, sender=Message)
def log_message_edit(sender, instance, **kwargs):
    """
    Track message edits by saving previous versions to MessageHistory.
    Creates a new history entry if message content has changed.
    """
    if instance.pk:  # Only for existing messages
        try:
            old_message = Message.objects.get(pk=instance.pk)
            if old_message.message_body != instance.message_body:
                latest_history = MessageHistory.objects.filter(
                    message=instance
                ).order_by('-version').first()
                
                next_version = (latest_history.version + 1) if latest_history else 1
                
                MessageHistory.objects.create(
                    message=instance,
                    old_content=old_message.message_body,
                    new_content=instance.message_body,
                    edited_by=instance.sender,
                    version=next_version,
                )
        except Message.DoesNotExist:
            pass


@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """
    Update conversation's updated_at when new messages are created.
    """
    if created:
        instance.conversation.save(update_fields=['updated_at'])


# ====================== Conversation Signals ======================
@receiver(m2m_changed, sender=Conversation.participants.through)
def create_group_notification(sender, instance, action, pk_set, **kwargs):
    """
    Handle notifications when users are added/removed from conversations.
    Creates appropriate notifications for all affected users.
    """
    if action == "post_add" and pk_set:
        conversation = instance
        added_users = User.objects.filter(pk__in=pk_set)
        
        for added_user in added_users:
            if conversation.is_group:
                title = "Added to group chat"
                content = f"You were added to '{conversation.title or 'a group chat'}'"
                
                Notification.objects.create(
                    recipient=added_user,
                    sender=conversation.created_by,
                    conversation=conversation,
                    notification_type='group_add',
                    title=title,
                    content=content,
                )
                
                for participant in conversation.participants.exclude(pk=added_user.pk):
                    Notification.objects.create(
                        recipient=participant,
                        sender=conversation.created_by,
                        conversation=conversation,
                        notification_type='group_add',
                        title="New member added",
                        content=f"{added_user.get_full_name()} was added to the group",
                    )
    
    elif action == "post_remove" and pk_set:
        conversation = instance
        removed_users = User.objects.filter(pk__in=pk_set)
        
        for removed_user in removed_users:
            if conversation.is_group:
                Notification.objects.create(
                    recipient=removed_user,
                    sender=conversation.created_by,
                    conversation=conversation,
                    notification_type='group_remove',
                    title="Removed from group chat",
                    content=f"You were removed from '{conversation.title or 'a group chat'}'",
                )
                
                for participant in conversation.participants.all():
                    Notification.objects.create(
                        recipient=participant,
                        sender=conversation.created_by,
                        conversation=conversation,
                        notification_type='group_remove',
                        title="Member removed",
                        content=f"{removed_user.get_full_name()} was removed from the group",
                    )


# ====================== MessageHistory Signals ======================
@receiver(post_save, sender=MessageHistory)
def create_edit_notification(sender, instance, created, **kwargs):
    """
    Create notifications when messages are edited.
    Notifies all conversation participants except the editor.
    """
    if created and instance.version > 1:  # Skip notification for initial version
        conversation = instance.message.conversation
        participants = conversation.participants.exclude(user_id=instance.edited_by.user_id)
        
        for participant in participants:
            Notification.objects.create(
                recipient=participant,
                sender=instance.edited_by,
                message=instance.message,
                conversation=conversation,
                notification_type='message_edit',
                title=f'{instance.edited_by.get_full_name()} edited a message',
                content=f'Message in "{conversation}" was edited'
            )


# ====================== Notification Signals ======================
@receiver(post_save, sender=Notification)
def log_notification_creation(sender, instance, created, **kwargs):
    """
    Log notification creation and potentially trigger delivery mechanisms.
    """
    if created:
        print(f"New notification created: {instance.notification_type} for {instance.recipient.username}")


# ====================== Helper Functions ======================
def mark_conversation_notifications_as_read(user, conversation):
    """
    Mark all notifications for a conversation as read for a user.
    Returns count of marked notifications.
    """
    notifications = Notification.objects.filter(
        recipient=user,
        conversation=conversation,
        is_read=False
    )
    count = notifications.update(is_read=True, read_at=timezone.now())
    return count


def get_unread_notification_count(user):
    """Get count of unread notifications for a user."""
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_recent_notifications(user, limit=20):
    """
    Get recent notifications for a user with related objects prefetched.
    Returns QuerySet of notifications ordered by most recent.
    """
    return Notification.objects.filter(
        recipient=user
    ).select_related(
        'sender', 'message', 'conversation'
    ).order_by('-created_at')[:limit]