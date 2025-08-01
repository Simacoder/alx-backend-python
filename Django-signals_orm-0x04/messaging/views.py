from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch, Q, Count

from .models import Conversation, Message
from .serializers import MessageSerializer, ConversationSerializer

User = get_user_model()

class OptimizedPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OptimizedPagination

    def get_queryset(self):
        """
        Uses both direct optimized query AND custom manager for demonstration
        """
        # Using custom manager
        return Message.unread.unread_for_user(self.request.user)
        
        # Alternative direct optimized query:
        # return Message.objects.filter(
        #     receiver=self.request.user,
        #     is_read=False
        # ).select_related('sender', 'conversation').only(
        #     'id', 'message_body', 'sent_at',
        #     'sender__id', 'sender__username',
        #     'conversation__id', 'conversation__title'
        # ).order_by('-sent_at')

    @action(detail=False, methods=['get'])
    def unread_inbox(self, request):
        """
        Uses custom manager for unread messages
        """
        unread_messages = Message.unread.unread_for_user(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Uses custom manager to ensure we only mark unread messages
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
    pagination_class = OptimizedPagination

    def get_queryset(self):
        """
        Hybrid approach using both direct optimized queries and manager
        """
        # Prefetch using custom manager
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related('created_by').prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.unread.unread_for_user(self.request.user),
                to_attr='unread_messages'
            ),
            'participants'
        ).only(
            'id', 'title', 'updated_at', 'created_by__username'
        ).order_by('-updated_at')

    @action(detail=True, methods=['get'])
    def unread_messages(self, request, pk=None):
        """
        Uses model method that internally uses custom manager
        """
        conversation = self.get_object()
        unread_messages = conversation.get_unread_messages(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = MessageSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_counts(self, request):
        """
        Uses both direct optimized query and manager
        """
        conversations = Conversation.objects.filter(
            participants=request.user
        ).annotate(
            unread_count=Count(
                'messages',
                filter=Q(messages__receiver=request.user) & 
                      Q(messages__is_read=False)
            )
        ).only('id', 'title')
        
         
        
        data = {
            str(conv.id): conv.unread_count
            for conv in conversations
        }
        return Response(data)