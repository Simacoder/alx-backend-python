from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from .models import Conversation, Message, MessageReadStatus
from .serializers import (
    UserSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReadSerializer,
    ConversationParticipantSerializer,
)
from .permissions import (
    IsParticipantOfConversation,
    ConversationPermissions,
    MessagePermissions,
    UserPermissions,
)

User = get_user_model()

class OptimizedPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100
    page_size_query_param = 'page_size'

class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsParticipantOfConversation, ConversationPermissions]
    pagination_class = OptimizedPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    ordering_fields = ['updated_at', 'created_at']
    ordering = ['-updated_at']

    def get_queryset(self):
        # Optimized prefetching for messages and participants
        message_prefetch = Prefetch(
            'messages',
            queryset=Message.objects.select_related('sender')
                                  .order_by('-created_at')[:1]
        )
        
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related('created_by').prefetch_related(
            'participants',
            message_prefetch
        ).annotate(
            unread_count=Count(
                'messages',
                filter=~Q(messages__read_status__user=self.request.user) |
                      Q(messages__read_status__is_read=False)
        ).distinct())

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        
        # Fully optimized message query with replies
        messages = conversation.messages.select_related(
            'sender', 'reply_to', 'reply_to__sender'
        ).prefetch_related(
            Prefetch(
                'replies',
                queryset=Message.objects.select_related('sender')
                                      .prefetch_related('read_status__user')
            ),
            Prefetch(
                'read_status',
                queryset=MessageReadStatus.objects.select_related('user')
            )
        ).order_by('-created_at')
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        conversation = self.get_object()
        
        # Bulk update read statuses
        unread_messages = Message.objects.filter(
            conversation=conversation
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        ).select_related('conversation')
        
        MessageReadStatus.objects.bulk_create(
            [
                MessageReadStatus(
                    message=msg,
                    user=request.user,
                    is_read=True,
                    read_at=timezone.now()
                ) for msg in unread_messages
            ],
            update_conflicts=True,
            update_fields=['is_read', 'read_at']
        )
        
        return Response(
            {'marked_read': unread_messages.count()},
            status=status.HTTP_200_OK
        )

class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsParticipantOfConversation, MessagePermissions]
    pagination_class = OptimizedPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        # Fully optimized query with all relationships
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related(
            'sender', 'conversation', 'reply_to', 'reply_to__sender'
        ).prefetch_related(
            Prefetch(
                'replies',
                queryset=Message.objects.select_related('sender')
            ),
            Prefetch(
                'read_status',
                queryset=MessageReadStatus.objects.select_related('user')
            )
        ).order_by('-created_at')

    def perform_create(self, serializer):
        message = serializer.save(sender=self.request.user)
        # Update conversation timestamp
        message.conversation.updated_at = timezone.now()
        message.conversation.save(update_fields=['updated_at'])

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Message.objects.filter(
            conversation__participants=request.user
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        ).count()
        return Response({'count': count})

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [UserPermissions]
    pagination_class = OptimizedPagination

    def get_queryset(self):
        return User.objects.all().prefetch_related(
            Prefetch(
                'conversations',
                queryset=Conversation.objects.annotate(
                    unread_count=Count(
                        'messages',
                        filter=~Q(messages__read_status__user=self.request.user)
                    )
                )
            )
        )

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def conversation_statistics(request):
    stats = {
        'unread_count': Message.objects.filter(
            conversation__participants=request.user
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        ).count()
    }
    return Response(stats)