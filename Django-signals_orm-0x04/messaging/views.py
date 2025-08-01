from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch
from django.db.models import Q

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
        Optimized query using select_related and only()
        """
        return Message.objects.filter(
            receiver=self.request.user,
            is_read=False
        ).select_related(
            'sender', 'conversation'
        ).only(
            'id', 'message_body', 'sent_at',
            'sender__id', 'sender__username',
            'conversation__id', 'conversation__title'
        ).order_by('-sent_at')

    @action(detail=False, methods=['get'])
    def unread_inbox(self, request):
        """
        Optimized unread inbox using select_related and only()
        """
        unread_messages = Message.objects.filter(
            receiver=request.user,
            is_read=False
        ).select_related(
            'sender', 'conversation'
        ).only(
            'id', 'message_body', 'sent_at',
            'sender__id', 'sender__username',
            'conversation__id', 'conversation__title'
        )
        
        page = self.paginate_queryset(unread_messages)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark message as read with optimized query
        """
        message = get_object_or_404(
            Message.objects.filter(receiver=request.user),
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
        Fully optimized conversation query with prefetch
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related(
            'created_by'
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.filter(
                    receiver=self.request.user,
                    is_read=False
                ).select_related('sender')
                .only(
                    'id', 'message_body', 'sent_at',
                    'sender__id', 'sender__username'
                ),
                to_attr='unread_messages'
            ),
            'participants'
        ).only(
            'id', 'title', 'updated_at', 'created_by__username'
        ).order_by('-updated_at')

    @action(detail=True, methods=['get'])
    def unread_messages(self, request, pk=None):
        """
        Optimized unread messages per conversation
        """
        conversation = self.get_object()
        unread_messages = Message.objects.filter(
            conversation=conversation,
            receiver=request.user,
            is_read=False
        ).select_related('sender').only(
            'id', 'message_body', 'sent_at',
            'sender__id', 'sender__username'
        )
        
        page = self.paginate_queryset(unread_messages)
        serializer = MessageSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def unread_counts(self, request):
        """
        Optimized unread counts using aggregation
        """
        from django.db.models import Count
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