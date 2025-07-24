# chats/filters.py
import django_filters
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta
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
    # Enhanced participant filtering by username
    participant_username = django_filters.CharFilter(method='filter_by_participant_username')
    participant_id = django_filters.NumberFilter(method='filter_by_participant_id')
    
    has_unread = django_filters.BooleanFilter(method='filter_has_unread')
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Date range filtering
    created_date_range = django_filters.DateFromToRangeFilter(field_name='created_at__date')
    updated_date_range = django_filters.DateFromToRangeFilter(field_name='updated_at__date')
    
    # Filter by conversation ID
    conversation_id = django_filters.CharFilter(field_name='conversation_id')
    
    class Meta:
        model = Conversation
        fields = ['title', 'is_group', 'created_by', 'participant', 'participant_username', 
                 'participant_id', 'has_unread', 'created_after', 'created_before', 
                 'updated_after', 'updated_before', 'conversation_id']
    
    def filter_by_participant(self, queryset, name, value):
        """
        Filter conversations by participant
        """
        if value:
            return queryset.filter(participants=value)
        return queryset
    
    def filter_by_participant_username(self, queryset, name, value):
        """
        Filter conversations by participant username
        """
        if value:
            return queryset.filter(participants__username__icontains=value).distinct()
        return queryset
    
    def filter_by_participant_id(self, queryset, name, value):
        """
        Filter conversations by participant user ID
        """
        if value:
            return queryset.filter(participants__user_id=value).distinct()
        return queryset
    
    def filter_has_unread(self, queryset, name, value):
        """
        Filter conversations that have unread messages for the current user
        """
        if value is not None and hasattr(self, 'request') and self.request.user.is_authenticated:
            user = self.request.user
            if value:
                # Conversations with unread messages (messages not marked as read by current user)
                return queryset.filter(
                    messages__isnull=False
                ).exclude(
                    messages__read_status__user=user,
                    messages__read_status__is_read=True
                ).exclude(
                    messages__sender=user
                ).distinct()
            else:
                # Conversations with all messages read
                return queryset.exclude(
                    messages__isnull=False
                ).exclude(
                    messages__read_status__user=user,
                    messages__read_status__is_read=False
                ).distinct()
        return queryset


class MessageFilter(django_filters.FilterSet):
    """
    Filter for messages with various options including time range filtering
    """
    content = django_filters.CharFilter(lookup_expr='icontains')
    sender = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    sender_username = django_filters.CharFilter(method='filter_by_sender_username')
    sender_id = django_filters.NumberFilter(field_name='sender__user_id')
    
    conversation = django_filters.ModelChoiceFilter(queryset=Conversation.objects.all())
    conversation_id = django_filters.CharFilter(field_name='conversation__conversation_id')
    
    is_read = django_filters.BooleanFilter(method='filter_is_read')
    is_edited = django_filters.BooleanFilter()
    is_deleted = django_filters.BooleanFilter()
    
    has_attachments = django_filters.BooleanFilter(method='filter_has_attachments')
    message_type = django_filters.CharFilter()
    reply_to = django_filters.ModelChoiceFilter(queryset=Message.objects.all())
    is_reply = django_filters.BooleanFilter(method='filter_is_reply')
    
    # Time range filters
    created_after = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name='updated_at', lookup_expr='lte')
    
    # Date range filtering (without time)
    created_date_range = django_filters.DateFromToRangeFilter(field_name='created_at__date')
    created_on = django_filters.DateFilter(field_name='created_at__date')
    
    # Time shortcuts
    today = django_filters.BooleanFilter(method='filter_today')
    this_week = django_filters.BooleanFilter(method='filter_this_week')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    
    # Filter messages with specific users (in conversations with them)
    with_user = django_filters.CharFilter(method='filter_with_user')
    with_user_id = django_filters.NumberFilter(method='filter_with_user_id')
    
    class Meta:
        model = Message
        fields = ['content', 'sender', 'sender_username', 'sender_id', 'conversation', 
                 'conversation_id', 'is_read', 'is_edited', 'is_deleted', 'has_attachments', 
                 'message_type', 'reply_to', 'is_reply', 'created_after', 'created_before', 
                 'updated_after', 'updated_before', 'created_date_range', 'created_on',
                 'today', 'this_week', 'this_month', 'with_user', 'with_user_id']
    
    def filter_by_sender_username(self, queryset, name, value):
        """
        Filter messages by sender username
        """
        if value:
            return queryset.filter(sender__username__icontains=value)
        return queryset
    
    def filter_is_read(self, queryset, name, value):
        """
        Filter messages by read status for current user
        """
        if value is not None and hasattr(self, 'request') and self.request.user.is_authenticated:
            user = self.request.user
            if value:
                return queryset.filter(
                    read_status__user=user,
                    read_status__is_read=True
                )
            else:
                return queryset.exclude(
                    read_status__user=user,
                    read_status__is_read=True
                )
        return queryset
    
    def filter_has_attachments(self, queryset, name, value):
        """
        Filter messages that have attachments
        """
        if value is not None:
            # Assuming you have an attachments field or related model
            # Adjust this based on your actual attachment implementation
            if hasattr(Message, 'attachments'):
                if value:
                    return queryset.filter(attachments__isnull=False).distinct()
                else:
                    return queryset.filter(attachments__isnull=True)
        return queryset
    
    def filter_is_reply(self, queryset, name, value):
        """
        Filter messages that are replies
        """
        if value is not None:
            if value:
                return queryset.filter(reply_to__isnull=False)
            else:
                return queryset.filter(reply_to__isnull=True)
        return queryset
    
    def filter_today(self, queryset, name, value):
        """
        Filter messages from today
        """
        if value:
            today = timezone.now().date()
            return queryset.filter(created_at__date=today)
        return queryset
    
    def filter_this_week(self, queryset, name, value):
        """
        Filter messages from this week
        """
        if value:
            today = timezone.now().date()
            week_start = today - timedelta(days=today.weekday())
            return queryset.filter(created_at__date__gte=week_start)
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        """
        Filter messages from this month
        """
        if value:
            today = timezone.now().date()
            month_start = today.replace(day=1)
            return queryset.filter(created_at__date__gte=month_start)
        return queryset
    
    def filter_with_user(self, queryset, name, value):
        """
        Filter messages from conversations with a specific user (by username)
        """
        if value and hasattr(self, 'request') and self.request.user.is_authenticated:
            return queryset.filter(
                conversation__participants__username__icontains=value
            ).exclude(sender=self.request.user).distinct()
        return queryset
    
    def filter_with_user_id(self, queryset, name, value):
        """
        Filter messages from conversations with a specific user (by user_id)
        """
        if value and hasattr(self, 'request') and self.request.user.is_authenticated:
            return queryset.filter(
                conversation__participants__user_id=value
            ).exclude(sender=self.request.user).distinct()
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
    is_staff = django_filters.BooleanFilter()
    
    # Date filters
    joined_after = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='gte')
    joined_before = django_filters.DateTimeFilter(field_name='date_joined', lookup_expr='lte')
    last_login_after = django_filters.DateTimeFilter(field_name='last_login', lookup_expr='gte')
    last_login_before = django_filters.DateTimeFilter(field_name='last_login', lookup_expr='lte')
    
    search = django_filters.CharFilter(method='filter_search')
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_online', 
                 'is_active', 'is_staff', 'joined_after', 'joined_before', 
                 'last_login_after', 'last_login_before', 'search']
    
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