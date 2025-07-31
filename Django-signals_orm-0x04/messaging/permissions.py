# messaging/permissions.py , updated for Django signals and ORM
from rest_framework import permissions


class BaseAuthenticatedPermission(permissions.BasePermission):
    """
    Base permission class that ensures user is authenticated and active.
    All other permissions inherit from this.
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated and active
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )


class ConversationPermissions(BaseAuthenticatedPermission):
    """
    Comprehensive permissions for conversation operations.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    
    Rules:
    - Only participants can access conversations
    - Only creator can delete conversations
    - Participants can update conversation details
    - Only group conversations allow participant management
    """
    
    def has_object_permission(self, request, view, obj):
        # Must be a participant to access conversation
        is_participant = obj.participants.filter(user_id=request.user.user_id).exists()
        if not is_participant:
            return False
        
        # DELETE: Only creator can delete conversations
        if request.method == 'DELETE' or view.action == 'destroy':
            return obj.created_by == request.user
        
        # PUT/PATCH: Participants can update conversation details
        if (request.method in ['PUT', 'PATCH'] or 
            view.action in ['update', 'partial_update', 'update_title']):
            return True
        
        # Participant management: Only for group conversations
        if view.action in ['add_participant', 'remove_participant']:
            return obj.is_group
        
        # GET/POST and other actions: All participants allowed
        return True


class MessagePermissions(BaseAuthenticatedPermission):
    """
    Comprehensive permissions for message operations.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    
    Rules:
    - Only conversation participants can access messages
    - Only message sender can modify/delete their own messages
    - All participants can read messages and mark them as read
    """
    
    def has_object_permission(self, request, view, obj):
        # Must be participant in the conversation to access messages
        is_participant = obj.conversation.participants.filter(user_id=request.user.user_id).exists()
        if not is_participant:
            return False
        
        # PUT/PATCH/DELETE: Only sender can modify their own messages
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj.sender == request.user
        
        # GET/POST and other actions: All participants allowed
        return True


class UserPermissions(BaseAuthenticatedPermission):
    """
    Permission class for user operations in chat context.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    
    Rules:
    - Users can only modify their own profile
    - Basic user info can be read by others (for chat functionality)
    """
    
    def has_object_permission(self, request, view, obj):
        # PUT/PATCH/DELETE: Users can only modify their own profile
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj == request.user
        
        # GET: Reading other users' basic info allowed for chat functionality
        return True


# Legacy/Specific Permission Classes (kept for backward compatibility)

class IsParticipantOfConversation(BaseAuthenticatedPermission):
    """
    Legacy permission class - use ConversationPermissions or MessagePermissions instead.
    Custom permission to only allow authenticated participants of a conversation to access it.
    """
    
    def has_object_permission(self, request, view, obj):
        # For Conversation objects
        if hasattr(obj, 'participants'):
            is_participant = obj.participants.filter(user_id=request.user.user_id).exists()
            
            if request.method == 'DELETE':
                return is_participant and obj.created_by == request.user
            elif request.method in ['PUT', 'PATCH']:
                return is_participant
            return is_participant
        
        # For Message objects
        if hasattr(obj, 'conversation'):
            is_participant = obj.conversation.participants.filter(user_id=request.user.user_id).exists()
            
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return is_participant and obj.sender == request.user
            return is_participant
        
        return False


class IsOwnerOrReadOnly(BaseAuthenticatedPermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Read permissions for any authenticated user, write permissions only for owner.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions (GET) are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions (POST, PUT, PATCH, DELETE) only for owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'sender'):
            return obj.sender == request.user
        
        return False


class IsMessageSender(BaseAuthenticatedPermission):
    """
    Custom permission to only allow the message sender to modify it.
    Participants can view, only sender can modify.
    """
    
    def has_object_permission(self, request, view, obj):
        # For GET requests, any participant can view
        if request.method in permissions.SAFE_METHODS:
            if hasattr(obj, 'conversation'):
                return obj.conversation.participants.filter(user_id=request.user.user_id).exists()
            return False
        
        # For PUT, PATCH, DELETE requests, only sender can modify
        if request.method in ['PUT', 'PATCH', 'DELETE']:
            if hasattr(obj, 'sender'):
                return obj.sender == request.user
        
        return False


class IsConversationCreator(BaseAuthenticatedPermission):
    """
    Custom permission to only allow the creator of a conversation to perform certain actions.
    """
    
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        return False


class CanModifyConversation(BaseAuthenticatedPermission):
    """
    Custom permission for conversation modification.
    Participants can update title and manage participants (for group chats).
    Only creator can delete the conversation.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is a participant
        if not obj.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For DELETE requests, only creator is allowed
        if request.method == 'DELETE' or view.action == 'destroy':
            return obj.created_by == request.user
        
        # For PUT/PATCH requests or update actions, any participant is allowed
        if request.method in ['PUT', 'PATCH'] or view.action in ['update', 'partial_update']:
            return True
        
        # For other modifications, any participant is allowed
        return True


class CanAccessMessage(BaseAuthenticatedPermission):
    """
    Custom permission for message access.
    Only participants can access messages.
    Only sender can modify/delete their own messages.
    """
    
    def has_object_permission(self, request, view, obj):
        # Check if user is participant in the conversation
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For PUT, PATCH, DELETE requests, only sender is allowed
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj.sender == request.user
        
        # For GET and POST requests, any participant is allowed
        return True


# Alias for backward compatibility
IsAuthenticatedAndActive = BaseAuthenticatedPermission