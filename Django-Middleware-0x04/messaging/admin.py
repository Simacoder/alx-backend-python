from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Message, Notification


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin interface for Message model with enhanced functionality.
    """
    list_display = [
        'id', 
        'sender_link', 
        'receiver_link', 
        'content_preview', 
        'timestamp', 
        'is_read',
        'notification_count'
    ]
    list_filter = [
        'is_read', 
        'timestamp', 
        'sender', 
        'receiver'
    ]
    search_fields = [
        'sender__username', 
        'receiver__username', 
        'content'
    ]
    readonly_fields = [
        'timestamp', 
        'notification_count',
        'created_notifications'
    ]
    fieldsets = [
        ('Message Details', {
            'fields': ('sender', 'receiver', 'content', 'is_read')
        }),
        ('Metadata', {
            'fields': ('timestamp', 'notification_count', 'created_notifications'),
            'classes': ['collapse']
        })
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    list_per_page = 20

    def sender_link(self, obj):
        """Create a clickable link to the sender's admin page."""
        url = reverse('admin:auth_user_change', args=[obj.sender.pk])
        return format_html('<a href="{}">{}</a>', url, obj.sender.username)
    sender_link.short_description = 'Sender'
    sender_link.admin_order_field = 'sender__username'

    def receiver_link(self, obj):
        """Create a clickable link to the receiver's admin page."""
        url = reverse('admin:auth_user_change', args=[obj.receiver.pk])
        return format_html('<a href="{}">{}</a>', url, obj.receiver.username)
    receiver_link.short_description = 'Receiver'
    receiver_link.admin_order_field = 'receiver__username'

    def content_preview(self, obj):
        """Show a truncated preview of the message content."""
        if len(obj.content) > 50:
            return f"{obj.content[:50]}..."
        return obj.content
    content_preview.short_description = 'Content Preview'

    def notification_count(self, obj):
        """Show the number of notifications created for this message."""
        count = obj.notifications.count()
        if count > 0:
            return format_html(
                '<span style="color: green; font-weight: bold;">{}</span>', 
                count
            )
        return format_html('<span style="color: red;">0</span>')
    notification_count.short_description = 'Notifications'

    def created_notifications(self, obj):
        """Show details of notifications created for this message."""
        notifications = obj.notifications.all()
        if not notifications:
            return "No notifications created"
        
        notification_list = []
        for notification in notifications:
            notification_list.append(
                f"• {notification.user.username} - {notification.title} "
                f"({'Read' if notification.is_read else 'Unread'})"
            )
        
        return format_html('<br>'.join(notification_list))
    created_notifications.short_description = 'Created Notifications'

    def get_queryset(self, request):
        """Optimize queryset to reduce database queries."""
        queryset = super().get_queryset(request)
        return queryset.select_related('sender', 'receiver').prefetch_related('notifications')

    actions = ['mark_as_read', 'mark_as_unread']

    def mark_as_read(self, request, queryset):
        """Admin action to mark selected messages as read."""
        updated = queryset.update(is_read=True)
        self.message(request, f'{updated} messages marked as read.')
    mark_as_read.short_description = 'Mark selected messages as read'

    def mark_as_unread(self, request, queryset):
        """Admin action to mark selected messages as unread."""
        updated = queryset.update(is_read=False)
        self.message(request, f'{updated} messages marked as unread.')
    mark_as_unread.short_description = 'Mark selected messages as unread'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin interface for Notification model with enhanced functionality.
    """
    list_display = [
        'id',
        'user_link',
        'notification_type',
        'title',
        'content_preview',
        'is_read',
        'created_at',
        'related_message_link'
    ]
    list_filter = [
        'notification_type',
        'is_read',
        'created_at',
        'user'
    ]
    search_fields = [
        'user__username',
        'title',
        'content',
        'message__content'
    ]
    readonly_fields = [
        'created_at',
        'related_message_details'
    ]
    fieldsets = [
        ('Notification Details', {
            'fields': ('user', 'notification_type', 'title', 'content', 'is_read')
        }),
        ('Related Message', {
            'fields': ('message', 'related_message_details'),
            'classes': ['collapse']
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ['collapse']
        })
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    list_per_page = 25

    def user_link(self, obj):
        """Create a clickable link to the user's admin page."""
        url = reverse('admin:auth_user_change', args=[obj.user.pk])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = 'User'
    user_link.admin_order_field = 'user__username'

    def content_preview(self, obj):
        """Show a truncated preview of the notification content."""
        if len(obj.content) > 40:
            return f"{obj.content[:40]}..."
        return obj.content
    content_preview.short_description = 'Content Preview'

    def related_message_link(self, obj):
        """Create a clickable link to the related message."""
        if obj.message:
            url = reverse('admin:messaging_message_change', args=[obj.message.pk])
            return format_html('<a href="{}">Message #{}</a>', url, obj.message.pk)
        return "No related message"
    related_message_link.short_description = 'Related Message'

    def related_message_details(self, obj):
        """Show details of the related message."""
        if not obj.message:
            return "No related message"
        
        return format_html(
            '<strong>From:</strong> {}<br>'
            '<strong>To:</strong> {}<br>'
            '<strong>Content:</strong> {}<br>'
            '<strong>Sent:</strong> {}',
            obj.message.sender.username,
            obj.message.receiver.username,
            obj.message.content[:100] + ('...' if len(obj.message.content) > 100 else ''),
            obj.message.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        )
    related_message_details.short_description = 'Related Message Details'

    def get_queryset(self, request):
        """Optimize queryset to reduce database queries."""
        queryset = super().get_queryset(request)
        return queryset.select_related('user', 'message', 'message__sender', 'message__receiver')

    actions = ['mark_as_read', 'mark_as_unread', 'delete_selected']

    def mark_as_read(self, request, queryset):
        """Admin action to mark selected notifications as read."""
        updated = queryset.update(is_read=True)
        self.message(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = 'Mark selected notifications as read'

    def mark_as_unread(self, request, queryset):
        """Admin action to mark selected notifications as unread."""
        updated = queryset.update(is_read=False)
        self.message(request, f'{updated} notifications marked as unread.')
    mark_as_unread.short_description = 'Mark selected notifications as unread'


# Custom admin site configuration
admin.site.site_header = "Messaging System Administration"
admin.site.site_title = "Messaging Admin"
admin.site.index_title = "Welcome to Messaging System Administration"