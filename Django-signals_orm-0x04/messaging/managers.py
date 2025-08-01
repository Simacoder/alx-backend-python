from django.db import models
from django.db.models import Q

class UnreadMessagesManager(models.Manager):
    """
    Custom manager for filtering unread messages for a specific user.
    """
    def unread_for_user(self, user):
        """
        Returns only unread messages for the specified user.
        Optimized with .only() to fetch only necessary fields.
        """
        return self.filter(
            Q(receiver=user) & Q(is_read=False)
        .select_related('sender', 'conversation')
        .only(
            'id', 'message_body', 'sent_at', 'is_read',
            'sender__id', 'sender__username',
            'conversation__id', 'conversation__title'
        ))