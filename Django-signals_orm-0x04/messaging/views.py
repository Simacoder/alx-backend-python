from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from rest_framework.pagination import PageNumberPagination

from .models import Conversation, Message
from .serializers import MessageSerializer, ConversationSerializer
from .managers import UnreadMessagesManager

User = get_user_model()

class MessagePagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        Uses custom manager to get unread messages with optimized query
        """
        return Message.unread.unread_for_user(self.request.user)

    @action(detail=False, methods=['get'])
    def unread_inbox(self, request):
        """
        Endpoint for user's unread inbox messages
        """
        unread_messages = Message.unread.unread_for_user(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark a specific message as read
        """
        message = get_object_or_404(
            Message.unread.unread_for_user(request.user),
            pk=pk
        )
        message.is_read = True
        message.save(update_fields=['is_read'])
        return Response({'status': 'message marked as read'})

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = MessagePagination

    def get_queryset(self):
        """
        Optimized conversation query with prefetch of unread messages
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.unread.unread_for_user(self.request.user),
                to_attr='unread_messages'
            )
        ).only(
            'id', 'title', 'updated_at'
        ).order_by('-updated_at')

    @action(detail=True, methods=['get'])
    def unread_messages(self, request, pk=None):
        """
        Get unread messages in a specific conversation
        """
        conversation = self.get_object()
        unread_messages = conversation.get_unread_messages(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = MessageSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_counts(self, request):
        """
        Get counts of unread messages per conversation
        """
        conversations = self.get_queryset()
        data = {
            str(conv.id): len(conv.unread_messages)
            for conv in conversations
        }
        return Response(data)