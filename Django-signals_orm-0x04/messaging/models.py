from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password
from django.conf import settings
import uuid
from django.db.models import Q, Prefetch
from django.utils import timezone


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


class UnreadMessagesManager(models.Manager):
    """
    Custom manager for filtering unread messages.
    """
    def for_user(self, user):
        return self.filter(
            Q(receiver=user) & Q(is_read=False)
        .select_related('sender', 'conversation')
        .only(
            'message_id', 'message_body', 'sent_at',
            'sender__user_id', 'sender__username',
            'conversation__conversation_id'
        ))


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
        indexes = [
            models.Index(fields=['-updated_at']),
        ]

    def __str__(self):
        if self.title:
            return self.title
        
        participants_names = [user.get_full_name() for user in self.participants.all()[:3]]
        if self.participants.count() > 3:
            participants_names.append(f"and {self.participants.count() - 3} others")
        
        return f"Conversation: {', '.join(participants_names)}"

    def get_unread_count(self, user):
        """
        Get count of unread messages for a specific user in this conversation.
        Uses the custom unread manager for optimized querying.
        """
        return self.messages.unread.for_user(user).count()

    def get_threaded_messages(self, depth=2):
        """
        Get all messages in this conversation with their replies up to specified depth
        using optimized queries with prefetch_related and select_related.
        """
        base_messages = self.messages.filter(parent_message__isnull=True)
        
        # Build the prefetch queries dynamically based on depth
        prefetch_chain = None
        for _ in range(depth):
            prefetch_chain = Prefetch(
                'replies',
                queryset=Message.objects.select_related('sender').prefetch_related(
                    prefetch_chain if prefetch_chain else None
                )
            )
        
        return base_messages.select_related('sender').prefetch_related(prefetch_chain)


class Message(models.Model):
    """
    Model representing a message within a conversation with threaded replies support.
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
    
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        help_text="User who should receive this message"
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
    
    parent_message = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Parent message this is a reply to"
    )

    # Managers
    objects = models.Manager()  # Default manager
    unread = UnreadMessagesManager()  # Custom manager for unread messages

    class Meta:
        db_table = 'messages'
        verbose_name = 'Message'
        verbose_name_plural = 'Messages'
        ordering = ['sent_at']
        indexes = [
            models.Index(fields=['conversation', '-sent_at']),
            models.Index(fields=['parent_message', 'sent_at']),
            models.Index(fields=['sender']),
            models.Index(fields=['receiver', 'is_read']),  # Added for unread messages optimization
        ]

    def __str__(self):
        preview = self.message_body[:50] + "..." if len(self.message_body) > 50 else self.message_body
        return f"{self.sender.username}: {preview}"

    def mark_as_read(self):
        """
        Mark the message as read and update the timestamp.
        """
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read', 'updated_at'])
            # Create or update read status
            MessageReadStatus.objects.update_or_create(
                message=self,
                user=self.receiver,
                defaults={'is_read': True, 'read_at': timezone.now()}
            )

    def get_thread(self, depth=3):
        """
        Get the complete thread of messages starting from this one.
        Uses recursive CTE for efficient querying of nested replies.
        """
        from django.db.models import F
        from django.db.models.expressions import RawSQL
        
        return Message.objects.raw("""
            WITH RECURSIVE message_tree AS (
                SELECT * FROM messages_message WHERE message_id = %s
                UNION ALL
                SELECT m.* FROM messages_message m
                JOIN message_tree mt ON m.parent_message_id = mt.message_id
                WHERE m.parent_message_id IS NOT NULL
                LIMIT 100  -- Prevent infinite recursion
            )
            SELECT * FROM message_tree
            ORDER BY sent_at
        """, [str(self.message_id)])

    def get_flattened_thread(self):
        """
        Get all messages in this thread in a flattened structure with level indicators.
        Returns a list of tuples (message, depth_level).
        """
        def flatten_replies(message, level=0):
            result = [(message, level)]
            for reply in message.replies.all():
                result.extend(flatten_replies(reply, level + 1))
            return result
        
        return flatten_replies(self)

    @property
    def is_reply(self):
        return self.parent_message is not None


class MessageReadStatus(models.Model):
    """
    Model for tracking message read status by users.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_statuses',
        help_text="The message being tracked"
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text="User who read/unread the message"
    )
    
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the message has been read"
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the message was read"
    )

    class Meta:
        db_table = 'message_read_status'
        verbose_name = 'Message Read Status'
        verbose_name_plural = 'Message Read Statuses'
        unique_together = ('message', 'user')
        indexes = [
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {'Read' if self.is_read else 'Unread'}"


def get_conversation_threads(conversation_id, max_depth=3):
    """
    Optimized query to get all message threads in a conversation.
    Uses prefetch_related with Prefetch objects to control query depth.
    """
    def build_prefetch(depth):
        if depth <= 1:
            return Prefetch('replies', 
                          queryset=Message.objects.select_related('sender', 'receiver'))
        return Prefetch('replies', 
                      queryset=Message.objects.select_related('sender', 'receiver').prefetch_related(
                          build_prefetch(depth - 1)
                      ))
    
    return Message.objects.filter(
        conversation_id=conversation_id,
        parent_message__isnull=True
    ).select_related('sender', 'receiver').prefetch_related(
        build_prefetch(max_depth)
    ).order_by('sent_at')