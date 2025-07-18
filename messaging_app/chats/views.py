# chats/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Conversation, Message, MessageReadStatus
from .serializers import (
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    ConversationTitleUpdateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReadSerializer,
    ConversationParticipantSerializer,
    UserSerializer
)
from .filters import ConversationFilter, MessageFilter, UserFilter

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for API responses
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing conversations.
    Provides CRUD operations for conversations with proper permissions.
    """
    serializer_class = ConversationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['title', 'participants__username', 'participants__first_name', 'participants__last_name']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']
    
    def get_queryset(self):
        """
        Get conversations for the authenticated user
        """
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related(
            'created_by'
        ).prefetch_related(
            'participants',
            'messages__sender'
        ).annotate(
            participant_count=Count('participants')
        ).order_by('-updated_at')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        elif self.action == 'update_title':
            return ConversationTitleUpdateSerializer
        return ConversationSerializer
    
    def perform_create(self, serializer):
        """
        Create a new conversation with the current user as creator
        """
        serializer.save(created_by=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new conversation
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Check if it's a direct conversation (2 participants)
        participant_ids = serializer.validated_data.get('participant_ids', [])
        if len(participant_ids) == 2:
            # Check if conversation between these users already exists
            existing_conversation = Conversation.objects.filter(
                is_group=False,
                participants__user_id__in=participant_ids
            ).annotate(
                participant_count=Count('participants')
            ).filter(participant_count=2).first()
            
            if existing_conversation:
                # Return existing conversation
                response_serializer = ConversationDetailSerializer(
                    existing_conversation,
                    context={'request': request}
                )
                return Response(
                    response_serializer.data,
                    status=status.HTTP_200_OK
                )
        
        # Create new conversation
        conversation = serializer.save()
        response_serializer = ConversationDetailSerializer(
            conversation,
            context={'request': request}
        )
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific conversation with messages
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update conversation (only title and participants)
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(conversation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete conversation (only creator can delete)
        """
        conversation = self.get_object()
        
        # Only creator can delete the conversation
        if conversation.created_by != request.user:
            return Response(
                {'error': 'Only the creator can delete this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        """
        Add a participant to the conversation
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow adding participants to group conversations
        if not conversation.is_group:
            return Response(
                {'error': 'Cannot add participants to direct conversations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ConversationParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, user_id=user_id)
        
        # Check if user is already a participant
        if conversation.participants.filter(user_id=user_id).exists():
            return Response(
                {'error': 'User is already a participant in this conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.participants.add(user)
        return Response(
            {'message': f'User {user.username} added to conversation'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """
        Remove a participant from the conversation
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only allow removing participants from group conversations
        if not conversation.is_group:
            return Response(
                {'error': 'Cannot remove participants from direct conversations'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ConversationParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, user_id=user_id)
        
        # Check if user is a participant
        if not conversation.participants.filter(user_id=user_id).exists():
            return Response(
                {'error': 'User is not a participant in this conversation'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Don't allow removing the creator
        if conversation.created_by == user:
            return Response(
                {'error': 'Cannot remove the conversation creator'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.participants.remove(user)
        return Response(
            {'message': f'User {user.username} removed from conversation'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['patch'])
    def update_title(self, request, pk=None):
        """
        Update conversation title
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        """
        Get list of conversation participants
        """
        conversation = self.get_object()
        
        # Check if user is participant
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        participants = conversation.participants.all()
        serializer = UserSerializer(participants, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search conversations by title or participant name
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversations = self.get_queryset().filter(
            Q(title__icontains=query) |
            Q(participants__username__icontains=query) |
            Q(participants__first_name__icontains=query) |
            Q(participants__last_name__icontains=query)
        ).distinct()
        
        page = self.paginate_queryset(conversations)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(conversations, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages.
    Provides CRUD operations for messages with proper permissions.
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__username', 'sender__first_name', 'sender__last_name']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Get messages for conversations the user is part of
        """
        conversation_id = self.request.query_params.get('conversation_id')
        
        base_queryset = Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related(
            'sender',
            'reply_to__sender',
            'conversation'
        ).order_by('-created_at')
        
        if conversation_id:
            base_queryset = base_queryset.filter(conversation_id=conversation_id)
        
        return base_queryset
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MessageUpdateSerializer
        return MessageSerializer
    
    def create(self, request, *args, **kwargs):
        """
        Create a new message in a conversation
        """
        conversation_id = request.data.get('conversation')
        if not conversation_id:
            return Response(
                {'error': 'conversation field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversation and check if user is participant
        conversation = get_object_or_404(Conversation, conversation_id=conversation_id)
        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create message data with sender
        message_data = request.data.copy()
        message_data['sender_id'] = request.user.user_id
        
        serializer = MessageSerializer(data=message_data)
        serializer.is_valid(raise_exception=True)
        message = serializer.save()
        
        # Update conversation's updated_at timestamp
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific message
        """
        message = self.get_object()
        
        # Check if user is participant in the conversation
        if not message.conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(message)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update a message (only sender can update)
        """
        message = self.get_object()
        
        # Only sender can update the message
        if message.sender != request.user:
            return Response(
                {'error': 'You can only update your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(message, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (only sender can delete)
        """
        message = self.get_object()
        
        # Only sender can delete the message
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        message.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['post'])
    def mark_as_read(self, request):
        """
        Mark messages as read
        """
        serializer = MessageReadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        message_ids = serializer.validated_data['message_ids']
        
        # Get messages that belong to conversations the user is part of
        messages = Message.objects.filter(
            message_id__in=message_ids,
            conversation__participants=request.user
        ).exclude(sender=request.user)  # Don't mark own messages as read
        
        # Mark messages as read
        updated_count = messages.update(is_read=True)
        
        # For group conversations, create read status records
        for message in messages.filter(conversation__is_group=True):
            MessageReadStatus.objects.get_or_create(
                message=message,
                user=request.user,
                defaults={'read_at': timezone.now()}
            )
        
        return Response(
            {'message': f'{updated_count} messages marked as read'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        """
        Get replies to a specific message
        """
        message = self.get_object()
        
        # Check if user is participant in the conversation
        if not message.conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response(
                {'error': 'You are not a participant in this conversation'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        replies = message.replies.select_related('sender').order_by('created_at')
        serializer = MessageSerializer(replies, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search messages by content
        """
        query = request.query_params.get('q', '')
        conversation_id = request.query_params.get('conversation_id')
        
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        messages = self.get_queryset().filter(content__icontains=query)
        
        if conversation_id:
            messages = messages.filter(conversation_id=conversation_id)
        
        page = self.paginate_queryset(messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(messages, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """
        Get unread messages for the current user
        """
        conversation_id = request.query_params.get('conversation_id')
        
        unread_messages = self.get_queryset().filter(
            is_read=False
        ).exclude(sender=request.user)
        
        if conversation_id:
            unread_messages = unread_messages.filter(conversation_id=conversation_id)
        
        page = self.paginate_queryset(unread_messages)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(unread_messages, many=True)
        return Response(serializer.data)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user operations related to chat functionality
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined']
    ordering = ['username']
    
    def get_queryset(self):
        """
        Get all users except the current user
        """
        return User.objects.exclude(user_id=self.request.user.user_id).order_by('username')
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        Search users by username, first name, or last name
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Search query parameter "q" is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = self.get_queryset().filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
        
        page = self.paginate_queryset(users)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def online(self, request):
        """
        Get list of online users
        """
        online_users = self.get_queryset().filter(is_online=True)
        serializer = self.get_serializer(online_users, many=True)
        return Response(serializer.data)


# Function-based views for specific endpoints
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_stats(request):
    """
    Get conversation statistics for the current user
    """
    user = request.user
    
    total_conversations = Conversation.objects.filter(participants=user).count()
    group_conversations = Conversation.objects.filter(participants=user, is_group=True).count()
    direct_conversations = total_conversations - group_conversations
    
    unread_messages = Message.objects.filter(
        conversation__participants=user,
        is_read=False
    ).exclude(sender=user).count()
    
    stats = {
        'total_conversations': total_conversations,
        'group_conversations': group_conversations,
        'direct_conversations': direct_conversations,
        'unread_messages': unread_messages
    }
    
    return Response(stats)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_conversations(request):
    """
    Get recent conversations for the current user (last 10)
    """
    conversations = Conversation.objects.filter(
        participants=request.user
    ).select_related('created_by').prefetch_related(
        'participants',
        'messages'
    ).order_by('-updated_at')[:10]
    
    serializer = ConversationSerializer(conversations, many=True, context={'request': request})
    return Response(serializer.data)