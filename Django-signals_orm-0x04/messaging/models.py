# messaging/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.conf import settings
import uuid


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    """
    user_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for the user"
    )
    
    password = models.CharField(
        max_length=128,
        help_text="User's hashed password"
    )
    
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
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username

    def save(self, *args, **kwargs):
        if self.password and not self.password.startswith(('pbkdf2_', 'bcrypt', 'argon2')):
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)


class Conversation(models.Model):
    """
    Model representing a conversation between users.
    """
    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the conversation"
    )
    
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='conversations',
        help_text="Users participating in this conversation"
    )
    
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
        
        participants_names = [user.get_full_name() for user in self.participants.all()[:3]]
        if self.participants.count() > 3:
            participants_names.append(f"and {self.participants.count() - 3} others")
        
        return f"Conversation: {', '.join(participants_names)}"

    @property
    def participant_count(self):
        return self.participants.count()

    def get_latest_message(self):
        return self.messages.order_by('-sent_at').first()

    def add_participant(self, user):
        self.participants.add(user)

    def remove_participant(self, user):
        self.participants.remove(user)


class Message(models.Model):
    """
    Model representing a message within a conversation.
    """
    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the message"
    )
    
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
    
    message_body = models.TextField(
        help_text="The actual message content"
    )
    
    sent_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Message sent timestamp"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last message update timestamp"
    )
    
    is_read = models.BooleanField(
        default=False,
        help_text="Indicates if the message has been read"
    )
    
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
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    def mark_as_edited(self):
        from django.utils import timezone
        
        self.is_edited = True
        self.edit_count += 1
        self.last_edited_at = timezone.now()
        self.save(update_fields=['is_edited', 'edit_count', 'last_edited_at', 'updated_at'])

    @property
    def is_reply(self):
        return self.reply_to is not None

    def get_edit_history(self):
        return self.edit_history.order_by('-edited_at')

    def get_original_content(self):
        first_history = self.edit_history.order_by('edited_at').first()
        return first_history.old_content if first_history else self.message_body


class MessageHistory(models.Model):
    """
    Model to track edit history of messages.
    """
    history_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the history entry"
    )
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='edit_history',
        help_text="Message this history entry belongs to"
    )
    
    old_content = models.TextField(
        help_text="Previous content of the message before edit"
    )
    
    new_content = models.TextField(
        help_text="New content of the message after edit"
    )
    
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_edits',
        help_text="User who edited the message"
    )
    
    edited_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the edit was made"
    )
    
    edit_reason = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Optional reason for the edit"
    )
    
    version = models.PositiveIntegerField(
        help_text="Version number of this edit"
    )

    class Meta:
        db_table = 'message_history'
        verbose_name = 'Message History'
        verbose_name_plural = 'Message Histories'
        ordering = ['-edited_at']
        
        indexes = [
            models.Index(fields=['message', '-edited_at']),
            models.Index(fields=['edited_by', '-edited_at']),
            models.Index(fields=['message', 'version']),
        ]
        
        unique_together = ['message', 'version']

    def __str__(self):
        return f"Edit v{self.version} of message {self.message.message_id} by {self.edited_by.username}"

    @property
    def content_changed(self):
        return self.old_content != self.new_content

    @property
    def content_diff_length(self):
        return len(self.new_content) - len(self.old_content)


class MessageReadStatus(models.Model):
    """
    Model to track which users have read which messages.
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
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('mention', 'Mention'),
        ('group_add', 'Added to Group'),
        ('group_remove', 'Removed from Group'),
        ('message_edit', 'Message Edited'),
    ]
    
    notification_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier for the notification"
    )
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who will receive this notification"
    )
    
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sent_notifications',
        help_text="User who triggered this notification"
    )
    
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Message that triggered this notification"
    )
    
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Conversation related to this notification"
    )
    
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
    
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the notification has been read"
    )
    
    is_sent = models.BooleanField(
        default=False,
        help_text="Whether the notification has been sent/delivered"
    )
    
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
        
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        return f"Notification to {self.recipient.username}: {self.title}"

    def mark_as_read(self):
        from django.utils import timezone
        
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])

    def mark_as_sent(self):
        if not self.is_sent:
            self.is_sent = True
            self.save(update_fields=['is_sent'])


# Utility functions for message editing (kept here as they're model-related)
def get_message_edit_history(message_id):
    try:
        message = Message.objects.get(message_id=message_id)
        return message.edit_history.order_by('version')
    except Message.DoesNotExist:
        return MessageHistory.objects.none()


def get_message_with_history(message_id):
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
    try:
        message = Message.objects.get(message_id=message_id)
        history_entry = MessageHistory.objects.get(
            message=message, 
            version=version_number
        )
        
        message.message_body = history_entry.old_content
        message.save()
        return True
    except (Message.DoesNotExist, MessageHistory.DoesNotExist):
        return False