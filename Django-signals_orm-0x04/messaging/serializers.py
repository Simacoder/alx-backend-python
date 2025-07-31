# chats/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Conversation, Message, MessageReadStatus

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model with basic information.
    Used for nested relationships and user listings.
    """
    full_name = serializers.ReadOnlyField(source='get_full_name')
    username = serializers.CharField(max_length=150, read_only=True)
    email = serializers.CharField(max_length=254, read_only=True)
    first_name = serializers.CharField(max_length=150, read_only=True)
    last_name = serializers.CharField(max_length=150, read_only=True)
    phone_number = serializers.CharField(max_length=20, read_only=True, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone_number', 'profile_picture', 'is_online',
            'last_seen', 'date_joined'
        ]
        read_only_fields = ['user_id', 'date_joined', 'last_seen']


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for User model.
    Includes additional fields for user profile management.
    """
    full_name = serializers.ReadOnlyField(source='get_full_name')
    username = serializers.CharField(max_length=150, read_only=True)
    email = serializers.CharField(max_length=254, read_only=True)
    first_name = serializers.CharField(max_length=150, allow_blank=True)
    last_name = serializers.CharField(max_length=150, allow_blank=True)
    phone_number = serializers.CharField(max_length=20, allow_blank=True, required=False)
    conversations_count = serializers.SerializerMethodField()
    sent_messages_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'user_id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone_number', 'profile_picture', 'is_online',
            'last_seen', 'date_joined', 'conversations_count', 'sent_messages_count'
        ]
        read_only_fields = [
            'user_id', 'date_joined', 'last_seen', 'conversations_count',
            'sent_messages_count'
        ]
    
    def get_conversations_count(self, obj):
        """Get the number of conversations the user is part of"""
        return obj.conversations.count()
    
    def get_sent_messages_count(self, obj):
        """Get the number of messages sent by the user"""
        return obj.sent_messages.count()


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    Includes sender information and reply handling.
    """
    sender = UserSerializer(read_only=True)
    sender_id = serializers.UUIDField(write_only=True)
    content = serializers.CharField(
        max_length=5000,
        min_length=1,
        help_text="Message content (1-5000 characters)",
        error_messages={
            'blank': 'Message content cannot be empty.',
            'max_length': 'Message content cannot exceed 5000 characters.'
        }
    )
    reply_to_message = serializers.SerializerMethodField()
    replies_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'sender_id', 'conversation',
            'content', 'reply_to', 'reply_to_message', 'replies_count',
            'is_read', 'is_edited', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'message_id', 'sender', 'is_read', 'is_edited',
            'created_at', 'updated_at', 'replies_count'
        ]
    
    def get_reply_to_message(self, obj):
        """Get basic information about the message being replied to"""
        if obj.reply_to:
            return {
                'message_id': obj.reply_to.message_id,
                'sender': obj.reply_to.sender.username,
                'content': obj.reply_to.content[:100] + "..." if len(obj.reply_to.content) > 100 else obj.reply_to.content,
                'created_at': obj.reply_to.created_at
            }
        return None
    
    def get_replies_count(self, obj):
        """Get the number of replies to this message"""
        return obj.replies.count()
    
    def validate_content(self, value):
        """Validate message content"""
        if not value or value.isspace():
            raise serializers.ValidationError("Message content cannot be empty or only whitespace.")
        
        # Remove excessive whitespace
        cleaned_content = ' '.join(value.split())
        if len(cleaned_content) < 1:
            raise serializers.ValidationError("Message content cannot be empty after cleaning.")
        
        return cleaned_content
    
    def validate_sender_id(self, value):
        """Validate that the sender exists"""
        try:
            User.objects.get(user_id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
    
    def validate_reply_to(self, value):
        """Validate that reply_to message exists and is in the same conversation"""
        if value and value.conversation != self.initial_data.get('conversation'):
            raise serializers.ValidationError(
                "Reply message must be in the same conversation"
            )
        return value
    
    def create(self, validated_data):
        """Create a new message with the sender from sender_id"""
        sender_id = validated_data.pop('sender_id')
        sender = User.objects.get(user_id=sender_id)
        return Message.objects.create(sender=sender, **validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating messages.
    Used in nested conversation serializers.
    """
    sender = UserSerializer(read_only=True)
    content = serializers.CharField(
        max_length=5000,
        min_length=1,
        help_text="Message content"
    )
    
    class Meta:
        model = Message
        fields = [
            'message_id', 'sender', 'content', 'reply_to',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['message_id', 'sender', 'created_at', 'updated_at']


class ConversationSerializer(serializers.ModelSerializer):
    """
    Basic serializer for Conversation model.
    Used for listing conversations without nested messages.
    """
    participants = UserSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    title = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
        help_text="Conversation title (optional for group chats)"
    )
    created_by = UserSerializer(read_only=True)
    participant_count = serializers.ReadOnlyField()
    latest_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'title', 'is_group', 'participants',
            'participant_ids', 'participant_count', 'created_by',
            'latest_message', 'unread_count', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'conversation_id', 'participant_count', 'created_by',
            'created_at', 'updated_at'
        ]
    
    def validate_title(self, value):
        """Validate conversation title"""
        if value and value.isspace():
            raise serializers.ValidationError("Title cannot be only whitespace.")
        return value.strip() if value else value
    
    def get_latest_message(self, obj):
        """Get the latest message in the conversation"""
        latest_message = obj.get_latest_message()
        if latest_message:
            return {
                'message_id': latest_message.message_id,
                'sender': latest_message.sender.username,
                'content': latest_message.content[:100] + "..." if len(latest_message.content) > 100 else latest_message.content,
                'created_at': latest_message.created_at
            }
        return None
    
    def get_unread_count(self, obj):
        """Get the number of unread messages for the current user"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(
                is_read=False
            ).exclude(sender=request.user).count()
        return 0
    
    def validate_participant_ids(self, value):
        """Validate that all participant IDs exist"""
        if value:
            existing_users = User.objects.filter(user_id__in=value)
            if existing_users.count() != len(value):
                raise serializers.ValidationError("One or more users do not exist")
        return value
    
    def create(self, validated_data):
        """Create a new conversation with participants"""
        participant_ids = validated_data.pop('participant_ids', [])
        request = self.context.get('request')
        
        # Set the creator
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        # Determine if it's a group conversation
        if len(participant_ids) > 2:
            validated_data['is_group'] = True
        
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        if participant_ids:
            users = User.objects.filter(user_id__in=participant_ids)
            conversation.participants.set(users)
        
        # Add the creator to participants if not already included
        if request and request.user.is_authenticated:
            conversation.participants.add(request.user)
        
        return conversation
    
    def update(self, instance, validated_data):
        """Update conversation with new participants"""
        participant_ids = validated_data.pop('participant_ids', None)
        
        # Update basic fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update participants if provided
        if participant_ids is not None:
            users = User.objects.filter(user_id__in=participant_ids)
            instance.participants.set(users)
            
            # Ensure creator is always a participant
            if instance.created_by:
                instance.participants.add(instance.created_by)
        
        instance.save()
        return instance


class ConversationDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for Conversation model.
    Includes nested messages and full participant information.
    """
    participants = UserSerializer(many=True, read_only=True)
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False
    )
    title = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
        help_text="Conversation title"
    )
    created_by = UserSerializer(read_only=True)
    messages = serializers.SerializerMethodField()
    participant_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Conversation
        fields = [
            'conversation_id', 'title', 'is_group', 'participants',
            'participant_ids', 'participant_count', 'created_by',
            'messages', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'conversation_id', 'participant_count', 'created_by',
            'created_at', 'updated_at'
        ]
    
    def get_messages(self, obj):
        """Get paginated messages for the conversation"""
        # Get latest 50 messages by default
        messages = obj.messages.select_related('sender', 'reply_to__sender').order_by('-created_at')[:50]
        return MessageSerializer(messages, many=True, context=self.context).data
    
    def create(self, validated_data):
        """Create a new conversation with participants"""
        participant_ids = validated_data.pop('participant_ids', [])
        request = self.context.get('request')
        
        # Set the creator
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        # Determine if it's a group conversation
        if len(participant_ids) > 2:
            validated_data['is_group'] = True
        
        conversation = Conversation.objects.create(**validated_data)
        
        # Add participants
        if participant_ids:
            users = User.objects.filter(user_id__in=participant_ids)
            conversation.participants.set(users)
        
        # Add the creator to participants if not already included
        if request and request.user.is_authenticated:
            conversation.participants.add(request.user)
        
        return conversation


class MessageReadStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for MessageReadStatus model.
    Used for tracking read status in group conversations.
    """
    user = UserSerializer(read_only=True)
    message = MessageSerializer(read_only=True)
    
    class Meta:
        model = MessageReadStatus
        fields = ['message', 'user', 'read_at']
        read_only_fields = ['read_at']


class ConversationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new conversations.
    Simplified version with validation.
    """
    title = serializers.CharField(
        max_length=200,
        allow_blank=True,
        required=False,
        help_text="Optional conversation title"
    )
    participant_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        help_text="List of user IDs to include in the conversation"
    )
    
    class Meta:
        model = Conversation
        fields = ['title', 'participant_ids']
    
    def validate_title(self, value):
        """Validate conversation title"""
        if value and value.isspace():
            raise serializers.ValidationError("Title cannot be only whitespace.")
        return value.strip() if value else value
    
    def validate_participant_ids(self, value):
        """Validate participant IDs and check for duplicates"""
        # Remove duplicates
        unique_ids = list(set(value))
        
        # Check if all users exist
        existing_users = User.objects.filter(user_id__in=unique_ids)
        if existing_users.count() != len(unique_ids):
            raise serializers.ValidationError("One or more users do not exist")
        
        # Check minimum participants (including creator)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if request.user.user_id not in unique_ids:
                unique_ids.append(request.user.user_id)
        
        if len(unique_ids) < 2:
            raise serializers.ValidationError("A conversation must have at least 2 participants")
        
        return unique_ids
    
    def create(self, validated_data):
        """Create conversation with proper participant management"""
        participant_ids = validated_data.pop('participant_ids')
        request = self.context.get('request')
        
        # Set creator and determine if it's a group
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        
        validated_data['is_group'] = len(participant_ids) > 2
        
        # Create conversation
        conversation = Conversation.objects.create(**validated_data)
        
        # Add all participants
        users = User.objects.filter(user_id__in=participant_ids)
        conversation.participants.set(users)
        
        return conversation


class MessageUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating messages.
    Only allows updating content and marks as edited.
    """
    content = serializers.CharField(
        max_length=5000,
        min_length=1,
        help_text="Updated message content",
        error_messages={
            'blank': 'Message content cannot be empty.',
            'max_length': 'Message content cannot exceed 5000 characters.'
        }
    )
    
    class Meta:
        model = Message
        fields = ['content']
    
    def validate_content(self, value):
        """Validate updated message content"""
        if not value or value.isspace():
            raise serializers.ValidationError("Message content cannot be empty or only whitespace.")
        
        # Remove excessive whitespace
        cleaned_content = ' '.join(value.split())
        if len(cleaned_content) < 1:
            raise serializers.ValidationError("Message content cannot be empty after cleaning.")
        
        return cleaned_content
    
    def update(self, instance, validated_data):
        """Update message content and mark as edited"""
        instance.content = validated_data.get('content', instance.content)
        instance.mark_as_edited()
        return instance


# Utility serializers for specific operations
class ConversationParticipantSerializer(serializers.Serializer):
    """
    Serializer for adding/removing participants from conversations.
    """
    user_id = serializers.UUIDField(help_text="User ID to add/remove")
    
    def validate_user_id(self, value):
        """Validate that the user exists"""
        try:
            User.objects.get(user_id=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")


class MessageReadSerializer(serializers.Serializer):
    """
    Serializer for marking messages as read.
    """
    message_ids = serializers.ListField(
        child=serializers.UUIDField(),
        help_text="List of message IDs to mark as read"
    )
    
    def validate_message_ids(self, value):
        """Validate that all message IDs exist"""
        existing_messages = Message.objects.filter(message_id__in=value)
        if existing_messages.count() != len(value):
            raise serializers.ValidationError("One or more messages do not exist")
        return value


class ConversationTitleUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating conversation titles.
    """
    title = serializers.CharField(
        max_length=200,
        allow_blank=True,
        help_text="New conversation title"
    )
    
    class Meta:
        model = Conversation
        fields = ['title']
    
    def validate_title(self, value):
        """Validate conversation title"""
        if value and value.isspace():
            raise serializers.ValidationError("Title cannot be only whitespace.")
        return value.strip() if value else value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile information.
    """
    first_name = serializers.CharField(
        max_length=150,
        allow_blank=True,
        required=False,
        help_text="User's first name"
    )
    last_name = serializers.CharField(
        max_length=150,
        allow_blank=True,
        required=False,
        help_text="User's last name"
    )
    phone_number = serializers.CharField(
        max_length=20,
        allow_blank=True,
        required=False,
        help_text="User's phone number"
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone_number']
    
    def validate_first_name(self, value):
        """Validate first name"""
        if value and value.isspace():
            raise serializers.ValidationError("First name cannot be only whitespace.")
        return value.strip() if value else value
    
    def validate_last_name(self, value):
        """Validate last name"""
        if value and value.isspace():
            raise serializers.ValidationError("Last name cannot be only whitespace.")
        return value.strip() if value else value
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        if value and not value.replace('+', '').replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit():
            raise serializers.ValidationError("Phone number must contain only digits and allowed formatting characters (+, -, spaces, parentheses).")
        return value.strip() if value else value