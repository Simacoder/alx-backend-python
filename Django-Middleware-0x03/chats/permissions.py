# chats/permissions.py
from rest_framework import permissions


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow authenticated participants of a conversation to access it.
    
    This permission ensures that:
    1. Only authenticated users can access the API
    2. Only participants in a conversation can send, view, update and delete messages
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check - user must be participant
        """
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
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
    def has_object_permission(self, request, view, obj):
        # Only allow the sender to modify their message
        if hasattr(obj, 'sender'):
            return obj.sender == request.user
        
        return False


class IsConversationCreator(permissions.BasePermission):
    """
    Custom permission to only allow the creator of a conversation to perform certain actions.
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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


# Enhanced Permission classes for different scenarios
class ConversationPermissions(permissions.BasePermission):
    """
    Combined permissions for conversation operations.
    Enforces that only authenticated participants can access conversations,
    and only participants can send, view, update messages.
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
    
    def has_object_permission(self, request, view, obj):
        # Must be a participant to access conversation
        if not obj.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # Different rules for different actions
        if view.action == 'destroy':
            # Only creator can delete
            return obj.created_by == request.user
        elif view.action in ['add_participant', 'remove_participant']:
            # Only group conversations allow participant management
            # And only participants can manage other participants
            return obj.is_group
        elif view.action in ['update', 'partial_update', 'update_title']:
            # Participants can update conversation details
            return True
        
        # Other actions (list, retrieve, create, mark_as_read) allowed for participants
        return True


class MessagePermissions(permissions.BasePermission):
    """
    Combined permissions for message operations.
    Enforces that only authenticated participants can access messages,
    and only participants can send, view, update and delete messages.
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
    
    def has_object_permission(self, request, view, obj):
        # Must be participant in the conversation to access messages
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # Only sender can modify/delete their messages
        if view.action in ['update', 'partial_update', 'destroy']:
            return obj.sender == request.user
        
        # Reading and marking as read allowed for all participants
        return True


# chats/permissions.py
from rest_framework import permissions


class IsParticipantOfConversation(permissions.BasePermission):
    """
    Custom permission to only allow authenticated participants of a conversation to access it.
    
    This permission ensures that:
    1. Only authenticated users can access the API
    2. Only participants in a conversation can send, view, update and delete messages
    3. Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
    def has_object_permission(self, request, view, obj):
        """
        Object-level permission check - user must be participant
        Applies to all HTTP methods including PUT, PATCH, DELETE
        """
        # For Conversation objects
        if hasattr(obj, 'participants'):
            is_participant = obj.participants.filter(user_id=request.user.user_id).exists()
            
            # For DELETE requests on conversations, only creator can delete
            if request.method == 'DELETE':
                return is_participant and obj.created_by == request.user
            
            # For PUT/PATCH requests on conversations, participants can update
            if request.method in ['PUT', 'PATCH']:
                return is_participant
            
            # For GET and POST, participants can access
            return is_participant
        
        # For Message objects
        if hasattr(obj, 'conversation'):
            is_participant = obj.conversation.participants.filter(user_id=request.user.user_id).exists()
            
            # For PUT/PATCH/DELETE requests on messages, only sender can modify
            if request.method in ['PUT', 'PATCH', 'DELETE']:
                return is_participant and obj.sender == request.user
            
            # For GET and POST, participants can access
            return is_participant
        
        return False


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
    def has_object_permission(self, request, view, obj):
        # Read permissions (GET) are allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions (POST, PUT, PATCH, DELETE) are only allowed to the owner
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        elif hasattr(obj, 'sender'):
            return obj.sender == request.user
        
        return False


class IsMessageSender(permissions.BasePermission):
    """
    Custom permission to only allow the sender of a message to modify it.
    Handles PUT, PATCH, DELETE methods for message modification.
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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


class IsConversationCreator(permissions.BasePermission):
    """
    Custom permission to only allow the creator of a conversation to perform certain actions.
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
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
        
        # For other modifications (add/remove participants), any participant is allowed
        return True


class CanAccessMessage(permissions.BasePermission):
    """
    Custom permission for message access.
    Only participants of the conversation can access messages.
    Only sender can modify/delete their own messages.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
    """
    
    def has_permission(self, request, view):
        """
        Global permission check - user must be authenticated
        """
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.is_active
        )
    
    def has_object_permission(self, request, view, obj):
        # Check if user is participant in the conversation
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For PUT, PATCH, DELETE requests or modification actions, only sender is allowed
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj.sender == request.user
        
        # For GET and POST requests, any participant is allowed
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


# Enhanced Permission classes for different scenarios
class ConversationPermissions(permissions.BasePermission):
    """
    Combined permissions for conversation operations.
    Enforces that only authenticated participants can access conversations,
    and only participants can send, view, update messages.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
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
    
    def has_object_permission(self, request, view, obj):
        # Must be a participant to access conversation
        if not obj.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For DELETE requests or destroy action, only creator can delete
        if request.method == 'DELETE' or view.action == 'destroy':
            return obj.created_by == request.user
        
        # For PUT/PATCH requests or update actions
        if (request.method in ['PUT', 'PATCH'] or 
            view.action in ['update', 'partial_update', 'update_title']):
            return True
        
        # For participant management actions
        if view.action in ['add_participant', 'remove_participant']:
            # Only group conversations allow participant management
            # And only participants can manage other participants
            return obj.is_group
        
        # Other actions (GET, POST, list, retrieve, create, mark_as_read) allowed for participants
        return True


class MessagePermissions(permissions.BasePermission):
    """
    Combined permissions for message operations.
    Enforces that only authenticated participants can access messages,
    and only participants can send, view, update and delete messages.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
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
    
    def has_object_permission(self, request, view, obj):
        # Must be participant in the conversation to access messages
        if not obj.conversation.participants.filter(user_id=request.user.user_id).exists():
            return False
        
        # For PUT, PATCH, DELETE requests or modification/deletion actions, only sender is allowed
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj.sender == request.user
        
        # For GET, POST and other actions (reading, marking as read), all participants are allowed
        return True


class UserPermissions(permissions.BasePermission):
    """
    Permission class for user operations in chat context.
    Handles all HTTP methods: GET, POST, PUT, PATCH, DELETE
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
    
    def has_object_permission(self, request, view, obj):
        # For PUT, PATCH, DELETE requests or modification actions, users can only access their own profile
        if (request.method in ['PUT', 'PATCH', 'DELETE'] or 
            view.action in ['update', 'partial_update', 'destroy']):
            return obj == request.user
        
        # For GET requests, reading other users' basic info is allowed for chat functionality
        return True