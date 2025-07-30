from django.db import models
from django.conf import settings  
from django.utils import timezone


class Message(models.Model):
    """
    Model representing a message between users.
    """
    sender = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.CASCADE,
    related_name='messaging_sent_messages',  
    help_text="User who sent the message"
   )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name='received_messages',
        help_text="User who receives the message"
    )
    content = models.TextField(
        max_length=1000,
        help_text="Message content"
    )
    timestamp = models.DateTimeField(
        default=timezone.now,
        help_text="When the message was sent"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the message has been read"
    )

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['receiver', '-timestamp']),
            models.Index(fields=['sender', '-timestamp']),
        ]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.receiver.username}"

    def mark_as_read(self):
        """Mark the message as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])


class Notification(models.Model):
    """
    Model representing notifications for users.
    """
    NOTIFICATION_TYPES = [
        ('message', 'New Message'),
        ('system', 'System Notification'),
        ('alert', 'Alert'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name='notifications',
        help_text="User who receives the notification"
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True,
        help_text="Related message (if applicable)"
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='message',
        help_text="Type of notification"
    )
    title = models.CharField(
        max_length=200,
        help_text="Notification title"
    )
    content = models.TextField(
        max_length=500,
        help_text="Notification content"
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the notification has been read"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the notification was created"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

    def mark_as_read(self):
        """Mark the notification as read."""
        self.is_read = True
        self.save(update_fields=['is_read'])

    @classmethod
    def create_message_notification(cls, message):
        """
        Create a notification for a new message.

        Args:
            message (Message): The message instance that triggered the notification

        Returns:
            Notification: The created notification instance
        """
        return cls.objects.create(
            user=message.receiver,
            message=message,
            notification_type='message',
            title=f'New message from {message.sender.username}',
            content=f'You have received a new message: "{message.content[:50]}{"..." if len(message.content) > 50 else ""}"'
        )
