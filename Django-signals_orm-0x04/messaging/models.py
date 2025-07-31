# messaging/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.conf import settings
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    
    This model extends the built-in User model to add additional fields
    specific to our messaging application requirements.
    """
    # Using UUID for primary key for better security and scalability
    user_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the user"
    )
    
    # Password field (inherited from AbstractUser, but adding custom save logic)
    password = models.CharField(
        max_length=128,
        help_text="User's hashed password"
    )
    
    # Additional user fields
    phone_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True,
        help_text="User's phone number"
    )
    
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', 
        blank=True, 
        null=True,
        help_text="User's profile picture"
    )
    
    is_online = models.BooleanField(
        default=False,
        help_text="Indicates if user is currently online"
    )
    
    last_seen = models.DateTimeField(
        auto_now=True,
        help_text="Last time user was active"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Account creation timestamp"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last account update timestamp"
    )

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} ({self.email})"

    def get_full_name(self):
        """Return user's full name or username if names are not set"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def save(self, *args, **kwargs):
        """Override save to hash password if it's being set"""
        if self.password and not self.password.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        """Set password using Django's built-in password hashing"""
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        """Check if the given raw password matches the stored password"""
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)


class Conversation(models.Model):
    """
    Model representing a conversation between users.
    
    A conversation can be between two or more users and contains
    metadata about the chat session.
    """
    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the conversation"
    )
    
    # Many-to-many relationship with Users
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Users participating in this conversation"
    )
    
    # Conversation metadata
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional conversation title/name"
    )
    
    is_group = models.BooleanField(
        default=False,
        help_text="Indicates if this is a group conversation"
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Conversation creation timestamp"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last conversation update timestamp"
    )
    
    # Admin/Creator of the conversation ( mainly for group chats)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_conversations',
        help_text="User who created this conversation"
    )

    class Meta:
        db_table = 'conversations'
        verbose_name = 'Conversation'
        verbose_name_plural = 'Conversations'
        ordering = ['-updated_at']

    def __str__(self):
        if self.title:
            return self.title
        
        # Generate a title based on participants
        participants_names = [user.get_full_name() for user in self.participants.all()[:3]]
        if self.participants.count() > 3:
            participants_names.append(f"and {self.participants.count() - 3} others")
        
        return f"Conversation: {', '.join(participants_names)}"

    @property
    def participant_count(self):
        """Return the number of participants in the conversation"""
        return self.participants.count()

    def get_latest_message(self):
        """Get the most recent message in this conversation"""
        return self.messages.order_by('-sent_at').first()

    def add_participant(self, user):
        """Add a user to the conversation"""
        self.participants.add(user)

    def remove_participant(self, user):
        """Remove a user from the conversation"""
        self.participants.remove(user)


class Message(models.Model):
    """
    Model representing a message within a conversation.
    
    Each message belongs to a conversation and has a sender.
    """
    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the message"
    )
    
    # Foreign key relationships
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text="User who sent this message"
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Conversation this message belongs to"
    )
    
    # Message content - renamed from 'content' to 'message_body'
    message_body = models.TextField(
        help_text="The actual message content"
    )
    
    # Message metadata - renamed from 'created_at' to 'sent_at'
    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Message sent timestamp"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last message update timestamp"
    )
    
    # Message status fields
    is_read = models.BooleanField(
        default=False,
        help_text="Indicates if the message has been read"
    )
    
    # UPDATED: Enhanced edit tracking with more details
    is_edited = models.BooleanField(
        default=False,
        help_text="Indicates if the message has been edited"
    )
    
    edit_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this message has been edited"
    )
    
    last_edited_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last edit"
    )
    
    #  Reply functionality
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Message this is a reply to"
    )

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['-sent_at']
        
        # Add database indexes for better query performance
        indexes = [
            models.Index(fields=['conversation', '-sent_at']),
            models.Index(fields=['sender', '-sent_at']),
            models.Index(fields=['is_read']),
            models.Index(fields=['is_edited']),
            models.Index(fields=['last_edited_at']),
        ]

    def __str__(self):
        content_preview = self.message_body[:50] + "..." if len(self.message_body) > 50 else self.message_body
        edit_indicator = " (edited)" if self.is_edited else ""
        return f"{self.sender.username}: {content_preview}{edit_indicator}"

    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    def mark_as_edited(self):
        """Mark this message as edited and update edit tracking"""
        from django.utils import timezone
        
        self.is_edited = True
        self.edit_count += 1
        self.last_edited_at = timezone.now()
        self.save(update_fields=['is_edited', 'edit_count', 'last_edited_at', 'updated_at'])

    @property
    def is_reply(self):
        """Check if this message is a reply to another message"""
        return self.reply_to is not None

    def get_edit_history(self):
        """Get all edit history entries for this message"""
        return self.edit_history.order_by('-edited_at')

    def get_original_content(self):
        """Get the original content of the message before any edits"""
        first_history = self.edit_history.order_by('edited_at').first()
        return first_history.old_content if first_history else self.message_body


class MessageHistory(models.Model):
    """
    Model to track edit history of messages.
    
    This model stores the previous versions of a message every time it's edited,
    allowing users to view the complete edit history.
    """
    history_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the history entry"
    )
    
    # The message this history entry belongs to
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='edit_history',
        help_text="Message this history entry belongs to"
    )
    
    # The content before the edit
    old_content = models.TextField(
        help_text="Previous content of the message before edit"
    )
    
    # The content after the edit (for reference)
    new_content = models.TextField(
        help_text="New content of the message after edit"
    )
    
    # User who made the edit
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_edits',
        help_text="User who edited the message"
    )
    
    # When the edit was made
    edited_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the edit was made"
    )
    
    # Edit reason (optional)
    edit_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional reason for the edit"
    )
    
    # Version number
    version = models.PositiveIntegerField(
        help_text="Version number of this edit"
    )

    class Meta:
        db_table = 'message_history'
        verbose_name = 'Message History'
        verbose_name_plural = 'Message Histories'
        ordering = ['-edited_at']
        
        # Ensure proper ordering and uniqueness
        indexes = [
            models.Index(fields=['message', '-edited_at']),
            models.Index(fields=['edited_by', '-edited_at']),
            models.Index(fields=['message', 'version']),
        ]
        
        # Ensure unique version numbers per message
        unique_together = ['message', 'version']

    def __str__(self):
        return f"Edit v{self.version} of message {self.message.message_id} by {self.edited_by.username}"

    @property
    def content_changed(self):
        """Check if the content actually changed"""
        return self.old_content != self.new_content

    @property
    def content_diff_length(self):
        """Get the difference in content length"""
        return len(self.new_content) - len(self.old_content)


class MessageReadStatus(models.Model):
    """
    Model to track which users have read which messages.
    
    This is useful for group conversations where you want to track
    read status per user.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_statuses'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_read_statuses'
    )
    
    read_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the message was read"
    )

    class Meta:
        db_table = 'message_read_statuses'
        unique_together = ['message', 'user']
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'

    def __str__(self):
        return f"{self.user.username} read message {self.message.message_id}"


class Notification(models.Model):
    """
    Model to store user notifications.
    
    This model tracks notifications sent to users for various events
    like new messages, mentions, etc.
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('mention', 'Mention'),
        ('group_add', 'Added to Group'),
        ('group_remove', 'Removed from Group'),
        ('message_edit', 'Message Edited'),  # NEW: Added for message edits
    ]
    
    notification_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the notification"
    )
    
    # The user who will receive the notification
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who will receive this notification"
    )
    
    # The user who triggered the notification 
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_notifications',
        help_text="User who triggered this notification"
    )
    
    # Related message (optional, for message notifications)
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Message that triggered this notification"
    )
    
    # Related conversation (optional)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Conversation related to this notification"
    )
    
    # Notification details
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='message',
        help_text="Type of notification"
    )
    
    title = models.CharField(
        max_length=255,
        help_text="Notification title"
    )
    
    content = models.TextField(
        help_text="Notification content/body"
    )
    
    # Notification status
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the notification has been read"
    )
    
    is_sent = models.BooleanField(
        default=False,
        help_text="Whether the notification has been sent/delivered"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Notification creation timestamp"
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when notification was read"
    )

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        
        # Add database indexes for better query performance
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"

    def mark_as_read(self):
        """Mark this notification as read"""
        from django.utils import timezone
        
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_sent(self):
        """Mark this notification as sent"""
        if not self.is_sent:
            self.is_sent = True
            self.save(update_fields=['is_sent'])


# SIGNAL HANDLERS
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """
    Update the conversation's updated_at timestamp when a new message is created.
    """
    if created:
        instance.conversation.save(update_fields=['updated_at'])


@receiver(pre_save, sender=Message)
def log_message_edit(sender, instance, **kwargs):
    """
    Log message edits by saving the old content to MessageHistory before updating.
    
    This signal fires before a message is saved. If the message already exists
    (has a primary key) and the content has changed, it creates a history entry.
    """
    # Only process if this is an update (not a new message)
    if instance.pk:
        try:
            # Get the current version from the database
            old_message = Message.objects.get(pk=instance.pk)
            
            # Check if the message content has actually changed
            if old_message.message_body != instance.message_body:
                # Get the next version number
                latest_history = MessageHistory.objects.filter(
                    message=instance
                ).order_by('-version').first()
                
                next_version = (latest_history.version + 1) if latest_history else 1
                
                # Create history entry with the old content
                MessageHistory.objects.create(
                    message=instance,
                    old_content=old_message.message_body,
                    new_content=instance.message_body,
                    edited_by=instance.sender,  # Assuming sender is the editor
                    version=next_version,
                    
                )
                
                # Mark the message as edited (this will be handled in mark_as_edited method)
                # We don't call mark_as_edited here to avoid recursion
                
        except Message.DoesNotExist:
            # This shouldn't happen, but handle gracefully
            pass


@receiver(post_save, sender=MessageHistory)
def create_edit_notification(sender, instance, created, **kwargs):
    """
    Create a notification when a message is edited.
    
    This can notify other participants in the conversation about the edit.
    """
    if created and instance.version > 1:  # Don't notify for the first "edit" (original content)
        # Get all participants in the conversation except the editor
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


# UTILITY FUNCTIONS FOR MESSAGE EDITING

def get_message_edit_history(message_id):
    """
    Utility function to get the complete edit history of a message.
    
    Args:
        message_id: UUID of the message
        
    Returns:
        QuerySet of MessageHistory objects ordered by version
    """
    try:
        message = Message.objects.get(message_id=message_id)
        return message.edit_history.order_by('version')
    except Message.DoesNotExist:
        return MessageHistory.objects.none()


def get_message_with_history(message_id):
    """
    Utility function to get a message along with its edit history.
    
    Args:
        message_id: UUID of the message
        
    Returns:
        Dictionary containing message and its history
    """
    try:
        message = Message.objects.get(message_id=message_id)
        history = message.edit_history.order_by('version')
        
        return {
            'message': message,
            'history': list(history),
            'edit_count': message.edit_count,
            'is_edited': message.is_edited,
            'last_edited_at': message.last_edited_at,
            'original_content': message.get_original_content()
        }
    except Message.DoesNotExist:
        return None


def restore_message_version(message_id, version_number, user):
    """
    Utility function to restore a message to a previous version.
    
    Args:
        message_id: UUID of the message
        version_number: Version to restore to
        user: User performing the restore operation
        
    Returns:
        Boolean indicating success
    """
    try:
        message = Message.objects.get(message_id=message_id)
        history_entry = MessageHistory.objects.get(
            message=message, 
            version=version_number
        )
        
        # Update message content to the old version
        message.message_body = history_entry.old_content
        message.save()  # This will trigger the pre_save signal to log the "restore" as an edit
        
        return True
    except (Message.DoesNotExist, MessageHistory.DoesNotExist):
        return False