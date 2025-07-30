# Create your models here.
# chats/models.py
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
    
    is_edited = models.BooleanField(
        default=False,
        help_text="Indicates if the message has been edited"
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
        ]

    def __str__(self):
        content_preview = self.message_body[:50] + "..." if len(self.message_body) > 50 else self.message_body
        return f"{self.sender.username}: {content_preview}"

    def mark_as_read(self):
        """Mark this message as read"""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])

    def mark_as_edited(self):
        """Mark this message as edited"""
        if not self.is_edited:
            self.is_edited = True
            self.save(update_fields=['is_edited', 'updated_at'])

    @property
    def is_reply(self):
        """Check if this message is a reply to another message"""
        return self.reply_to is not None


# Optional: Message read status tracking (for group chats)
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


# Signal handlers to automatically update conversation timestamps
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Message)
def update_conversation_timestamp(sender, instance, created, **kwargs):
    """
    Update the conversation's updated_at timestamp when a new message is created.
    """
    if created:
        instance.conversation.save(update_fields=['updated_at'])