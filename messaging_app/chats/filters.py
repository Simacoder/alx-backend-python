# chats/filters.py
import django_filters
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Conversation, Message

User = get_user_model()


class ConversationFilter(django_filters.FilterSet):
    """
    Filter for conversations with various options
    """
    title = django_filters.CharFilter(lookup_expr='icontains')
    is_group = django_filters.BooleanFilter()
    created_by = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    participant = django_filters.ModelChoiceFilter(
        queryset=User.objects.all(),
        method='filter_by_participant'
    )
    has_unread = django_filters.BooleanFilter(method='filter_has_unread')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    class Meta:
        model = Conversation
        fields = ['title', 'is_group', 'created_by', 'participant', 'has_unread', 
                 'created_after', 'created_before', 'updated_after', 'updated_before']
    
    def filter_by_participant(self, queryset, name, value):
        """
        Filter conversations by participant
        """
        if value:
            return queryset.filter(participants=value)
        return queryset
    
    def filter_has_unread(self, queryset, name, value):
        """
        Filter conversations that have unread messages for the current user
        """
        if value is not None:
            user = self.request.user
            if value:
                return queryset.filter(
                    messages__is_read=False,
                    messages__sender__ne=user
                ).distinct()
            else:
                return queryset.exclude(
                    messages__is_read=False,
                    messages__sender__ne=user
                ).distinct()
        return queryset


class MessageFilter(django_filters.FilterSet):
    """
    Filter for messages with various options
    """
    content = django_filters.CharFilter(lookup_expr='icontains')
    sender = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    conversation = django_filters.ModelChoiceFilter(queryset=Conversation.objects.all())
    is_read = django_filters.BooleanFilter()
    is_edited = django_filters.BooleanFilter()
    has_attachments = django_filters.BooleanFilter(method='filter_has_attachments')
    message_type = django_filters.CharFilter()
    reply_to = django_filters.ModelChoiceFilter(queryset=Message.objects.all())
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    class Meta:
        model = Message
        fields = ['content', 'sender', 'conversation', 'is_read', 'is_edited', 
                 'has_attachments', 'message_type', 'reply_to', 'created_after', 
                 'created_before', 'updated_after', 'updated_before']
    
    def filter_has_attachments(self, queryset, name, value):
        """
        Filter messages that have attachments
        """
        if value is not None:
            if value:
                return queryset.filter(attachments__isnull=False).distinct()
            else:
                return queryset.filter(attachments__isnull=True)
        return queryset


class UserFilter(django_filters.FilterSet):
    """
    Filter for users with various options
    """
    username = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    is_online = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_online', 
                 'is_active', 'search']
    
    def filter_search(self, queryset, name, value):
        """
        Search across multiple user fields
        """
        if value:
            return queryset.filter(
                Q(username__icontains=value) |
                Q(first_name__icontains=value) |
                Q(last_name__icontains=value) |
                Q(email__icontains=value)
            )
        return queryset