from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, permissions, generics
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from django.db.models import Prefetch, Q, Count
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.cache import cache

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
        Optimized query using custom manager with caching
        """
        cache_key = f"user_{self.request.user.id}_unread_messages"
        cached_messages = cache.get(cache_key)
        
        if cached_messages is not None:
            return cached_messages
            
        messages = Message.unread.for_user(self.request.user)
        cache.set(cache_key, messages, 60)  # Cache for 60 seconds
        return messages

    @method_decorator(cache_page(60))
    @action(detail=False, methods=['get'])
    def unread_inbox(self, request):
        """
        Cached endpoint for user's unread inbox
        """
        unread_messages = Message.unread.for_user(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark message as read and clear relevant cache
        """
        message = get_object_or_404(
            Message.unread.for_user(request.user),
            pk=pk
        )
        message.is_read = True
        message.save(update_fields=['is_read'])
        
        # Clear cache for this user's messages
        cache.delete(f"user_{request.user.id}_unread_messages")
        return Response({'status': 'message marked as read'})

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = OptimizedPagination

    def get_queryset(self):
        """
        Optimized conversation query with caching
        """
        cache_key = f"user_{self.request.user.id}_conversations"
        cached_conversations = cache.get(cache_key)
        
        if cached_conversations is not None:
            return cached_conversations
            
        conversations = Conversation.objects.filter(
            participants=self.request.user
        ).select_related('created_by').prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.unread.for_user(self.request.user),
                to_attr='unread_messages'
            ),
            'participants'
        ).only(
            'id', 'title', 'updated_at', 'created_by__username'
        ).order_by('-updated_at')
        
        cache.set(cache_key, conversations, 60)  # Cache for 60 seconds
        return conversations

    @method_decorator(cache_page(60))
    @action(detail=True, methods=['get'])
    def unread_messages(self, request, pk=None):
        """
        Cached endpoint for unread messages in conversation
        """
        conversation = self.get_object()
        unread_messages = conversation.get_unread_messages(request.user)
        page = self.paginate_queryset(unread_messages)
        serializer = MessageSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @method_decorator(cache_page(60))
    @action(detail=False, methods=['get'])
    def unread_counts(self, request):
        """
        Cached endpoint for unread message counts
        """
        cache_key = f"user_{request.user.id}_unread_counts"
        cached_counts = cache.get(cache_key)
        
        if cached_counts is not None:
            return Response(cached_counts)
            
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
        
        cache.set(cache_key, data, 60)  # Cache for 60 seconds
        return Response(data)

    @action(detail=True, methods=['post'])
    def mark_all_as_read(self, request, pk=None):
        """
        Mark all messages in conversation as read and clear cache
        """
        conversation = self.get_object()
        unread_messages = conversation.messages.filter(
            receiver=request.user,
            is_read=False
        )
        
        unread_messages.update(is_read=True)
        
        # Clear relevant cache
        cache.delete(f"user_{request.user.id}_unread_messages")
        cache.delete(f"user_{request.user.id}_unread_counts")
        cache.delete(f"user_{request.user.id}_conversations")
        
        return Response(
            {'status': f'{unread_messages.count()} messages marked as read'}
        )