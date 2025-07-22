# chats/views.py
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
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
from .permissions import (
    IsParticipantOfConversation,
    ConversationPermissions,
    MessagePermissions,
    IsAuthenticatedAndActive
)

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
    Provides CRUD operations for conversations with JWT authentication.
    """
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticatedAndActive, ConversationPermissions]
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
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        """
        Update conversation (only title and participants)
        """
        partial = kwargs.pop('partial', False)
        conversation = self.get_object()
        serializer = self.get_serializer(conversation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        """
        Remove a participant from the conversation
        """
        conversation = self.get_object()
        
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
        
        # Don't allow removing the conversation creator
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
        Update only the conversation title
        """
        conversation = self.get_object()
        serializer = self.get_serializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Conversation title updated successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark all messages in the conversation as read for the current user
        """
        conversation = self.get_object()
        
        # Get all unread messages for this user in this conversation
        unread_messages = Message.objects.filter(
            conversation=conversation
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        )
        
        # Mark all as read
        for message in unread_messages:
            MessageReadStatus.objects.update_or_create(
                message=message,
                user=request.user,
                defaults={'is_read': True, 'read_at': timezone.now()}
            )
        
        return Response(
            {'message': f'Marked {unread_messages.count()} messages as read'},
            status=status.HTTP_200_OK
        )


class MessageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing messages within conversations.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticatedAndActive, MessagePermissions]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        """
        Get messages for conversations where the user is a participant
        """
        return Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related(
            'sender',
            'conversation',
            'reply_to'
        ).prefetch_related(
            'read_status',
            'read_status__user'
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MessageUpdateSerializer
        elif self.action == 'mark_as_read':
            return MessageReadSerializer
        return MessageSerializer
    
    def perform_create(self, serializer):
        """
        Create a new message with the current user as sender
        """
        serializer.save(sender=self.request.user)
    
    def create(self, request, *args, **kwargs):
        """
        Create a new message in a conversation
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Get the conversation to update its updated_at timestamp
        conversation = serializer.validated_data['conversation']
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        
        message = serializer.save()
        response_serializer = MessageSerializer(message, context={'request': request})
        
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """
        Update a message (only content and edited status)
        """
        partial = kwargs.pop('partial', False)
        message = self.get_object()
        
        # Only allow the sender to edit their own messages
        if message.sender != request.user:
            return Response(
                {'error': 'You can only edit your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(message, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Mark message as edited
        message.is_edited = True
        message.edited_at = timezone.now()
        
        self.perform_update(serializer)
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete a message (soft delete)
        """
        message = self.get_object()
        
        # Only allow the sender to delete their own messages
        if message.sender != request.user:
            return Response(
                {'error': 'You can only delete your own messages'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Soft delete
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=['is_deleted', 'deleted_at'])
        
        return Response(
            {'message': 'Message deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """
        Mark a specific message as read for the current user
        """
        message = self.get_object()
        
        # Don't mark own messages as read
        if message.sender == request.user:
            return Response(
                {'error': 'Cannot mark your own message as read'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        read_status, created = MessageReadStatus.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True, 'read_at': timezone.now()}
        )
        
        action = 'marked' if created else 'updated'
        return Response(
            {'message': f'Message {action} as read'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get the count of unread messages for the current user
        """
        unread_count = Message.objects.filter(
            conversation__participants=request.user
        ).exclude(
            sender=request.user
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        ).count()
        
        return Response(
            {'unread_count': unread_count},
            status=status.HTTP_200_OK
        )


@api_view(['GET'])
@permission_classes([IsAuthenticatedAndActive])
def search_users(request):
    """
    Search for users to add to conversations
    """
    query = request.GET.get('q', '')
    if not query:
        return Response(
            {'error': 'Query parameter "q" is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Search users excluding the current user
    users = User.objects.filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(
        user_id=request.user.user_id
    ).filter(
        is_active=True
    )[:10]  # Limit to 10 results
    
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticatedAndActive])
def conversation_statistics(request):
    """
    Get conversation statistics for the current user
    """
    user = request.user
    
    # Get user's conversations
    user_conversations = Conversation.objects.filter(participants=user)
    
    # Calculate statistics
    total_conversations = user_conversations.count()
    group_conversations = user_conversations.filter(is_group=True).count()
    direct_conversations = user_conversations.filter(is_group=False).count()
    
    # Get message statistics
    total_messages_sent = Message.objects.filter(sender=user).count()
    total_messages_received = Message.objects.filter(
        conversation__participants=user
    ).exclude(sender=user).count()
    
    # Get unread count
    unread_messages = Message.objects.filter(
        conversation__participants=user
    ).exclude(
        sender=user
    ).exclude(
        read_status__user=user,
        read_status__is_read=True
    ).count()
    
    return Response({
        'conversations': {
            'total': total_conversations,
            'group': group_conversations,
            'direct': direct_conversations
        },
        'messages': {
            'sent': total_messages_sent,
            'received': total_messages_received,
            'unread': unread_messages
        }
    }, status=status.HTTP_200_OK)