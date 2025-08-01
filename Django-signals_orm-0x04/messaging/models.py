from django.db import models
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch
import uuid
from .managers import UnreadMessagesManager

User = get_user_model()

class Message(models.Model):
    """
    Message model with custom unread messages manager.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    conversation = models.ForeignKey('Conversation', related_name='messages', on_delete=models.CASCADE)
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    parent_message = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='replies')

    # Managers
    objects = models.Manager()  # Default manager
    unread = UnreadMessagesManager()  # Custom manager for unread messages

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['receiver', 'is_read']),
            models.Index(fields=['conversation', '-sent_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender} to {self.receiver}"

class Conversation(models.Model):
    """
    Conversation model with participants and messages.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    participants = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation {self.id}"

    def get_unread_messages(self, user):
        """
        Uses the custom manager to get unread messages in this conversation.
        """
        return self.messages.unread.unread_for_user(user)