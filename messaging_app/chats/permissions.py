# customise permissions.py
# chats/permissions.py
from rest_framework import permissions


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow participants of a conversation to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # For Conversation objects
        if hasattr(obj, 'participants'):
            return obj.participants.filter(user_id=request.user.user_id).exists()
        
        # For Message objects
        if hasattr(obj, 'conversation'):
            return obj.conversation.participants.filter(user_id=request.user.user_id).exists()
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'sender'):
            return obj.sender == request.user
        
        return False


class IsMessageSender(permissions.BasePermission):
    """
    Custom permission to only allow the sender of a message to modify it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Only allow the sender to modify their message
        if hasattr(obj, 'sender'):
            return obj.sender == request.user
        
        return False


class IsConversationCreator(permissions.BasePermission):
    """
    Custom permission to only allow the creator of a conversation to perform certain actions.
    """
    
    def has_object_permission(self, request, view, obj):
        # Only allow the creator to perform certain actions
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class CanModifyConversation(permissions.BasePermission):
    """
    Custom permission for conversation modification.
    Participants can update title and add/remove participants (for group chats).
    Only creator can delete the conversation.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is a participant
        if not obj.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For deletion, only creator is allowed
        if view.action == 'destroy':
            return obj.created_by == request.user
        
        # For other modifications, any participant is allowed
        return True


class CanAccessMessage(permissions.BasePermission):
    """
    Custom permission for message access.
    Only participants of the conversation can access messages.
    Only sender can modify/delete their own messages.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is participant in the conversation
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For modification/deletion, only sender is allowed
        if view.action in ['update', 'partial_update', 'destroy']:
            return obj.sender == request.user
        
        # For reading, any participant is allowed
        return True


class IsAuthenticatedAndActive(permissions.BasePermission):
    """
    Custom permission to only allow active authenticated users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_active
        )


# Permission classes for different scenarios
class ConversationPermissions(permissions.BasePermission):
    """
    Combined permissions for conversation operations
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Must be a participant
        if not obj.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # Different rules for different actions
        if view.action == 'destroy':
            # Only creator can delete
            return obj.created_by == request.user
        elif view.action in ['add_participant', 'remove_participant']:
            # Only group conversations allow participant management
            return obj.is_group
        
        # Other actions allowed for participants
        return True


class MessagePermissions(permissions.BasePermission):
    """
    Combined permissions for message operations
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Must be participant in the conversation
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # Only sender can modify/delete their messages
        if view.action in ['update', 'partial_update', 'destroy']:
            return obj.sender == request.user
        
        # Reading allowed for all participants
        return True