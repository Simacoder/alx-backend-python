from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q, Count
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    User, Conversation, Message, MessageReadStatus
)
from .serializers import (
    UserSerializer,
    ConversationSerializer,
    ConversationDetailSerializer,
    ConversationCreateSerializer,
    ConversationTitleUpdateSerializer,
    MessageSerializer,
    MessageCreateSerializer,
    MessageUpdateSerializer,
    MessageReadSerializer,
    ConversationParticipantSerializer,
)
from .permissions import (
    IsAuthenticatedAndActive,
    IsParticipantOfConversation,
    ConversationPermissions,
    MessagePermissions,
    UserPermissions,
)
from .filters import ConversationFilter, MessageFilter, UserFilter


User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer
    permission_classes = [IsParticipantOfConversation, ConversationPermissions]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = ConversationFilter
    search_fields = ['title', 'participants__username', 'participants__first_name', 'participants__last_name']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']

    def get_queryset(self):
        return Conversation.objects.filter(
            participants=self.request.user
        ).select_related('created_by').prefetch_related(
            'participants', 'messages__sender'
        ).annotate(participant_count=Count('participants')).order_by('-updated_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return ConversationCreateSerializer
        elif self.action == 'retrieve':
            return ConversationDetailSerializer
        elif self.action == 'update_title':
            return ConversationTitleUpdateSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        participant_ids = serializer.validated_data.get('participant_ids', [])
        if len(participant_ids) == 2:
            existing_conversation = Conversation.objects.filter(
                is_group=False,
                participants__user_id__in=participant_ids
            ).annotate(
                participant_count=Count('participants')
            ).filter(participant_count=2).first()
            if existing_conversation:
                response_serializer = ConversationDetailSerializer(existing_conversation, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_200_OK)
        conversation = serializer.save()
        response_serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()
        serializer = self.get_serializer(conversation)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        conversation = self.get_object()
        serializer = self.get_serializer(conversation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_participant(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.is_group:
            return Response({'error': 'Cannot add participants to direct conversations'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ConversationParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, user_id=user_id)

        if conversation.participants.filter(user_id=user_id).exists():
            return Response({'error': 'User is already a participant'}, status=status.HTTP_400_BAD_REQUEST)

        conversation.participants.add(user)
        return Response({'message': f'User {user.username} added'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_participant(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.is_group:
            return Response({'error': 'Cannot remove participants from direct conversations'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ConversationParticipantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_id = serializer.validated_data['user_id']
        user = get_object_or_404(User, user_id=user_id)

        if not conversation.participants.filter(user_id=user_id).exists():
            return Response({'error': 'User is not a participant'}, status=status.HTTP_400_BAD_REQUEST)
        if conversation.created_by == user:
            return Response({'error': 'Cannot remove the conversation creator'}, status=status.HTTP_400_BAD_REQUEST)

        conversation.participants.remove(user)
        return Response({'message': f'User {user.username} removed'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['patch'])
    def update_title(self, request, pk=None):
        conversation = self.get_object()
        serializer = self.get_serializer(conversation, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Title updated successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        conversation = self.get_object()
        unread_messages = Message.objects.filter(conversation=conversation).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        )
        for message in unread_messages:
            MessageReadStatus.objects.update_or_create(
                message=message,
                user=request.user,
                defaults={'is_read': True, 'read_at': timezone.now()}
            )
        return Response({'message': f'Marked {unread_messages.count()} messages as read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def by_conversation_id(self, request):
        """Get conversation by conversation_id query parameter"""
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response({'error': 'conversation_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            serializer = ConversationDetailSerializer(conversation, context={'request': request})
            return Response(serializer.data)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)


class MessageViewSet(viewsets.ModelViewSet):
    serializer_class = MessageSerializer
    permission_classes = [IsParticipantOfConversation, MessagePermissions]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MessageFilter
    search_fields = ['content', 'sender__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        # Allow filtering by conversation_id if provided
        queryset = Message.objects.filter(
            conversation__participants=self.request.user
        ).select_related('sender', 'conversation', 'reply_to').prefetch_related(
            'read_status', 'read_status__user'
        )
        
        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            queryset = queryset.filter(conversation__conversation_id=conversation_id)
            
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return MessageCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MessageUpdateSerializer
        elif self.action == 'mark_as_read':
            return MessageReadSerializer
        return MessageSerializer

    def perform_create(self, serializer):
        serializer.save(sender=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Handle both conversation and conversation_id
        conversation = None
        if 'conversation' in serializer.validated_data:
            conversation = serializer.validated_data['conversation']
        elif 'conversation_id' in request.data:
            try:
                conversation = Conversation.objects.get(
                    conversation_id=request.data['conversation_id'],
                    participants=request.user
                )
                serializer.validated_data['conversation'] = conversation
            except Conversation.DoesNotExist:
                return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        
        if not conversation:
            return Response({'error': 'Conversation is required'}, status=status.HTTP_400_BAD_REQUEST)

        if not conversation.participants.filter(user_id=request.user.user_id).exists():
            return Response({'error': 'Not a participant'}, status=status.HTTP_403_FORBIDDEN)

        conversation.updated_at = timezone.now()
        conversation.save(update_fields=['updated_at'])
        message = serializer.save()
        response_serializer = MessageSerializer(message, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        message = self.get_object()
        if message.sender != request.user:
            return Response({'error': 'Can only edit own messages'}, status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(message, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        message.is_edited = True
        message.edited_at = timezone.now()
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        message = self.get_object()
        if message.sender != request.user:
            return Response({'error': 'Can only delete own messages'}, status=status.HTTP_403_FORBIDDEN)
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=['is_deleted', 'deleted_at'])
        return Response({'message': 'Deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        message = self.get_object()
        if message.sender == request.user:
            return Response({'error': 'Cannot mark own message as read'}, status=status.HTTP_400_BAD_REQUEST)

        read_status, created = MessageReadStatus.objects.update_or_create(
            message=message,
            user=request.user,
            defaults={'is_read': True, 'read_at': timezone.now()}
        )
        action_str = 'marked' if created else 'updated'
        return Response({'message': f'Message {action_str} as read'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        unread_count = Message.objects.filter(
            conversation__participants=request.user
        ).exclude(
            read_status__user=request.user,
            read_status__is_read=True
        ).count()
        return Response({'unread_count': unread_count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def by_conversation_id(self, request):
        """Get messages by conversation_id"""
        conversation_id = request.query_params.get('conversation_id')
        if not conversation_id:
            return Response({'error': 'conversation_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            messages = Message.objects.filter(
                conversation=conversation
            ).select_related('sender', 'reply_to').prefetch_related(
                'read_status', 'read_status__user'
            ).order_by('-created_at')
            
            page = self.paginate_queryset(messages)
            if page is not None:
                serializer = MessageSerializer(page, many=True, context={'request': request})
                return self.get_paginated_response(serializer.data)
            
            serializer = MessageSerializer(messages, many=True, context={'request': request})
            return Response(serializer.data)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def mark_conversation_as_read(self, request):
        """Mark all messages in a conversation as read by conversation_id"""
        conversation_id = request.data.get('conversation_id')
        if not conversation_id:
            return Response({'error': 'conversation_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            conversation = Conversation.objects.get(
                conversation_id=conversation_id,
                participants=request.user
            )
            unread_messages = Message.objects.filter(conversation=conversation).exclude(
                read_status__user=request.user,
                read_status__is_read=True
            )
            for message in unread_messages:
                MessageReadStatus.objects.update_or_create(
                    message=message,
                    user=request.user,
                    defaults={'is_read': True, 'read_at': timezone.now()}
                )
            return Response({'message': f'Marked {unread_messages.count()} messages as read'}, status=status.HTTP_200_OK)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [UserPermissions]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = UserFilter
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'username']
    ordering = ['-date_joined']

    def get_queryset(self):
        return User.objects.all()

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    query = request.query_params.get('q', '')
    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query)
    )
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def conversation_statistics(request):
    user = request.user
    conversations = Conversation.objects.filter(participants=user)

    stats = {
        'total_conversations': conversations.count(),
        'group_conversations': conversations.filter(is_group=True).count(),
        'direct_conversations': conversations.filter(is_group=False).count(),
        'total_messages': Message.objects.filter(conversation__in=conversations).count(),
    }
    return Response(stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def recent_conversations(request):
    conversations = Conversation.objects.filter(
        participants=request.user
    ).order_by('-updated_at')[:10]
    serializer = ConversationSerializer(conversations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def conversation_by_id(request):
    """Get conversation by conversation_id parameter"""
    conversation_id = request.query_params.get('conversation_id')
    if not conversation_id:
        return Response({'error': 'conversation_id parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        conversation = Conversation.objects.get(
            conversation_id=conversation_id,
            participants=request.user
        )
        serializer = ConversationDetailSerializer(conversation, context={'request': request})
        return Response(serializer.data)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)


class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        user = serializer.save()
        # Optionally, generate JWT tokens after registration, or send email confirmation


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user