# Register your models here.
# chats/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User, Conversation, Message, MessageReadStatus


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin configuration for the User model.
    """
    list_display = [
        'username', 'email', 'first_name', 'last_name', 
        'is_online', 'last_seen', 'date_joined'
    ]
    
    list_filter = [
        'is_online', 'is_staff', 'is_active', 'date_joined', 'last_seen'
    ]
    
    search_fields = ['username', 'email', 'first_name', 'last_name', 'phone_number']
    
    ordering = ['-date_joined']
    
    readonly_fields = ['user_id', 'date_joined', 'last_login', 'last_seen']
    
    # Add custom fields to the user admin
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {
            'fields': ('user_id', 'phone_number', 'profile_picture', 'is_online', 'last_seen')
        }),
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Additional Info', {
            'fields': ('phone_number', 'profile_picture')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related()


class MessageInline(admin.TabularInline):
    """
    Inline admin for messages within a conversation.
    """
    model = Message
    extra = 0
    readonly_fields = ['message_id', 'sent_at', 'updated_at', 'is_read', 'is_edited']
    fields = ['sender', 'message_body', 'reply_to', 'is_read', 'is_edited', 'sent_at']
    
    def get_queryset(self, request):
        """Optimize queryset for inline"""
        return super().get_queryset(request).select_related('sender').order_by('-sent_at')


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Conversation model.
    """
    list_display = [
        'conversation_id', 'title', 'is_group', 'participant_count', 
        'created_by', 'created_at', 'updated_at'
    ]
    
    list_filter = ['is_group', 'created_at', 'updated_at']
    
    search_fields = ['title', 'participants__username', 'participants__email']
    
    readonly_fields = ['conversation_id', 'created_at', 'updated_at', 'participant_count']
    
    filter_horizontal = ['participants']
    
    inlines = [MessageInline]
    
    def participant_count(self, obj):
        """Display participant count in list view"""
        return obj.participant_count
    participant_count.short_description = 'Participants'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related('created_by').prefetch_related('participants')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for the Message model.
    """
    list_display = [
        'message_id', 'sender', 'conversation_title', 'content_preview', 
        'is_read', 'is_edited', 'sent_at'
    ]
    
    list_filter = [
        'is_read', 'is_edited', 'sent_at', 'updated_at',
        'conversation__is_group'
    ]
    
    search_fields = [
        'message_body', 'sender__username', 'sender__email', 
        'conversation__title'
    ]
    
    readonly_fields = [
        'message_id', 'sent_at', 'updated_at', 'is_read', 'is_edited'
    ]
    
    raw_id_fields = ['sender', 'conversation', 'reply_to']
    
    date_hierarchy = 'sent_at'
    
    def conversation_title(self, obj):
        """Display conversation title or generated name"""
        return str(obj.conversation)
    conversation_title.short_description = 'Conversation'
    
    def content_preview(self, obj):
        """Display truncated message content"""
        if len(obj.message_body) > 100:
            return obj.message_body[:100] + "..."
        return obj.message_body
    content_preview.short_description = 'Content'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related('sender', 'conversation')


@admin.register(MessageReadStatus)
class MessageReadStatusAdmin(admin.ModelAdmin):
    """
    Admin configuration for the MessageReadStatus model.
    """
    list_display = ['message_preview', 'user', 'read_at']
    
    list_filter = ['read_at', 'message__conversation__is_group']
    
    search_fields = [
        'user__username', 'user__email', 'message__message_body',
        'message__sender__username'
    ]
    
    raw_id_fields = ['message', 'user']
    
    date_hierarchy = 'read_at'
    
    def message_preview(self, obj):
        """Display message preview"""
        content = obj.message.message_body
        if len(content) > 50:
            content = content[:50] + "..."
        return f"{obj.message.sender.username}: {content}"
    message_preview.short_description = 'Message'
    
    def get_queryset(self, request):
        """Optimize queryset for admin list view"""
        return super().get_queryset(request).select_related('message__sender', 'user')


# Customize admin site headers
admin.site.site_header = "Messaging App Administration"
admin.site.site_title = "Messaging App Admin"
admin.site.index_title = "Welcome to Messaging App Administration"