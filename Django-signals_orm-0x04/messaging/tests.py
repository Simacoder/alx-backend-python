# messaging/tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, m2m_changed
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock
from .models import User, Conversation, Message, Notification, MessageReadStatus
from .signals import create_message_notification, create_group_notification

User = get_user_model()


class NotificationSignalTests(TestCase):
    """
    Test cases for notification signals and automatic notification creation.
    """
    
    def setUp(self):
        """Set up test data"""
        # Create test users
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        
        self.user3 = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123'
        )
        
        # Create a conversation
        self.conversation = Conversation.objects.create(
            title="Test Conversation",
            is_group=False,
            created_by=self.user1
        )
        self.conversation.participants.add(self.user1, self.user2)
    
    def test_message_notification_creation_private_chat(self):
        """Test that notifications are created when a message is sent in private chat"""
        # Count initial notifications
        initial_count = Notification.objects.count()
        
        # Create a message
        message = Message.objects.create(
            sender=self.user1,
            conversation=self.conversation,
            message_body="Hello Bob, how are you?"
        )
        
        # Check that notification was created
        self.assertEqual(Notification.objects.count(), initial_count + 1)
        
        # Get the created notification
        notification = Notification.objects.latest('created_at')
        
        # Verify notification details
        self.assertEqual(notification.recipient, self.user2)
        self.assertEqual(notification.sender, self.user1)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.conversation, self.conversation)
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.user1.get_full_name(), notification.title)
        self.assertIn(message.message_body, notification.content)
        self.assertFalse(notification.is_read)
        self.assertFalse(notification.is_sent)
    
    def test_message_notification_creation_group_chat(self):
        """Test that notifications are created for all group members except sender"""
        # Create a group conversation
        group_conversation = Conversation.objects.create(
            title="Test Group",
            is_group=True,
            created_by=self.user1
        )
        group_conversation.participants.add(self.user1, self.user2, self.user3)
        
        # Count initial notifications
        initial_count = Notification.objects.count()
        
        # Create a message in the group
        message = Message.objects.create(
            sender=self.user1,
            conversation=group_conversation,
            message_body="Hello everyone!"
        )
        
        # Check that notifications were created for all participants except sender
        new_notifications = Notification.objects.count() - initial_count
        self.assertEqual(new_notifications, 2)  # For user2 and user3
        
        # Verify notifications were created for correct recipients
        notifications = Notification.objects.filter(message=message)
        recipients = [n.recipient for n in notifications]
        self.assertIn(self.user2, recipients)
        self.assertIn(self.user3, recipients)
        self.assertNotIn(self.user1, recipients)  # Sender should not receive notification
        
        # Verify notification content for group messages
        for notification in notifications:
            self.assertEqual(notification.sender, self.user1)
            self.assertEqual(notification.message, message)
            self.assertEqual(notification.conversation, group_conversation)
            self.assertEqual(notification.notification_type, 'message')
            self.assertIn("Test Group", notification.title)
    
    def test_no_notification_for_message_update(self):
        """Test that notifications are not created when a message is updated"""
        # Create a message first
        message = Message.objects.create(
            sender=self.user1,
            conversation=self.conversation,
            message_body="Original message"
        )
        
        # Count notifications after message creation
        count_after_creation = Notification.objects.count()
        
        # Update the message
        message.message_body = "Updated message"
        message.mark_as_edited()
        message.save()
        
        # Verify no new notifications were created
        self.assertEqual(Notification.objects.count(), count_after_creation)
    
    def test_group_participant_addition_notification(self):
        """Test notifications when users are added to a group conversation"""
        # Create a group conversation with initial participants
        group_conversation = Conversation.objects.create(
            title="Test Group",
            is_group=True,
            created_by=self.user1
        )
        group_conversation.participants.add(self.user1, self.user2)
        
        # Count initial notifications
        initial_count = Notification.objects.count()
        
        # Add user3 to the group
        group_conversation.participants.add(self.user3)
        
        # Check that notifications were created
        new_notifications = Notification.objects.count() - initial_count
        self.assertGreaterEqual(new_notifications, 1)  # At least one for the added user
        
        # Verify notification for added user
        added_user_notification = Notification.objects.filter(
            recipient=self.user3,
            notification_type='group_add'
        ).first()
        
        self.assertIsNotNone(added_user_notification)
        self.assertEqual(added_user_notification.conversation, group_conversation)
        self.assertIn("Added to group", added_user_notification.title)
    
    def test_group_participant_removal_notification(self):
        """Test notifications when users are removed from a group conversation"""
        # Create a group conversation with participants
        group_conversation = Conversation.objects.create(
            title="Test Group",
            is_group=True,
            created_by=self.user1
        )
        group_conversation.participants.add(self.user1, self.user2, self.user3)
        
        # Count initial notifications
        initial_count = Notification.objects.count()
        
        # Remove user3 from the group
        group_conversation.participants.remove(self.user3)
        
        # Check that notifications were created
        new_notifications = Notification.objects.count() - initial_count
        self.assertGreaterEqual(new_notifications, 1)  # At least one for the removed user
        
        # Verify notification for removed user
        removed_user_notification = Notification.objects.filter(
            recipient=self.user3,
            notification_type='group_remove'
        ).first()
        
        self.assertIsNotNone(removed_user_notification)
        self.assertEqual(removed_user_notification.conversation, group_conversation)
        self.assertIn("Removed from group", removed_user_notification.title)
    
    def test_notification_model_methods(self):
        """Test Notification model methods"""
        # Create a notification
        notification = Notification.objects.create(
            recipient=self.user2,
            sender=self.user1,
            notification_type='message',
            title="Test Notification",
            content="This is a test notification"
        )
        
        # Test initial state
        self.assertFalse(notification.is_read)
        self.assertFalse(notification.is_sent)
        self.assertIsNone(notification.read_at)
        
        # Test mark_as_read method
        notification.mark_as_read()
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)
        
        # Test mark_as_sent method
        notification.mark_as_sent()
        notification.refresh_from_db()
        self.assertTrue(notification.is_sent)
        
        # Test string representation
        expected_str = f"Notification to {self.user2.username}: Test Notification"
        self.assertEqual(str(notification), expected_str)
    
    def test_bulk_notification_creation_performance(self):
        """Test that bulk notification creation is used for better performance"""
        # Create a large group conversation
        group_conversation = Conversation.objects.create(
            title="Large Group",
            is_group=True,
            created_by=self.user1
        )
        
        # Add many participants
        participants = [self.user1, self.user2, self.user3]
        for i in range(5):  # Add 5 more users
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            participants.append(user)
        
        group_conversation.participants.add(*participants)
        
        # Mock bulk_create to verify it's being called
        with patch.object(Notification.objects, 'bulk_create') as mock_bulk_create:
            mock_bulk_create.return_value = []
            
            # Create a message
            message = Message.objects.create(
                sender=self.user1,
                conversation=group_conversation,
                message_body="Hello large group!"
            )
            
            # Verify bulk_create was called
            mock_bulk_create.assert_called_once()
            
            # Verify the correct number of notifications were prepared for creation
            call_args = mock_bulk_create.call_args[0][0]  # First positional argument
            self.assertEqual(len(call_args), len(participants) - 1)  # All except sender


class NotificationQueryTests(TestCase):
    """
    Test cases for notification query methods and helper functions.
    """
    
    def setUp(self):
        """Set up test data"""
        self.user1 = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        
        self.user2 = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        
        # Create test notifications
        self.notification1 = Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            notification_type='message',
            title="Test Notification 1",
            content="Content 1"
        )
        
        self.notification2 = Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            notification_type='message',
            title="Test Notification 2",
            content="Content 2",
            is_read=True
        )
    
    def test_unread_notification_count(self):
        """Test getting unread notification count"""
        from .signals import get_unread_notification_count
        
        # Test for user1 (has 1 unread notification)
        count = get_unread_notification_count(self.user1)
        self.assertEqual(count, 1)
        
        # Test for user2 (has no notifications)
        count = get_unread_notification_count(self.user2)
        self.assertEqual(count, 0)
        
        # Mark notification as read and test again
        self.notification1.mark_as_read()
        count = get_unread_notification_count(self.user1)
        self.assertEqual(count, 0)
    
    def test_recent_notifications(self):
        """Test getting recent notifications"""
        from .signals import get_recent_notifications
        
        # Get recent notifications for user1
        recent = get_recent_notifications(self.user1, limit=10)
        self.assertEqual(len(recent), 2)
        
        # Verify ordering (most recent first)
        self.assertEqual(recent[0], self.notification2)
        self.assertEqual(recent[1], self.notification1)
        
        # Test limit functionality
        recent = get_recent_notifications(self.user1, limit=1)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0], self.notification2)
    
    def test_mark_conversation_notifications_as_read(self):
        """Test marking conversation notifications as read"""
        from .signals import mark_conversation_notifications_as_read
        
        # Create a conversation and related notifications
        conversation = Conversation.objects.create(
            title="Test Conversation",
            created_by=self.user1
        )
        
        # Create notifications for this conversation
        notif1 = Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            conversation=conversation,
            notification_type='message',
            title="Conversation Notification 1",
            content="Content 1"
        )
        
        notif2 = Notification.objects.create(
            recipient=self.user1,
            sender=self.user2,
            conversation=conversation,
            notification_type='message',
            title="Conversation Notification 2",
            content="Content 2"
        )
        
        # Verify notifications are unread
        self.assertFalse(notif1.is_read)
        self.assertFalse(notif2.is_read)
        
        # Mark conversation notifications as read
        count = mark_conversation_notifications_as_read(self.user1, conversation)
        self.assertEqual(count, 2)
        
        # Verify notifications are now read
        notif1.refresh_from_db()
        notif2.refresh_from_db()
        self.assertTrue(notif1.is_read)
        self.assertTrue(notif2.is_read)


class SignalIntegrationTests(TestCase):
    """
    Integration tests to ensure signals work correctly with the overall system.
    """
    
    def test_signal_handlers_are_connected(self):
        """Test that signal handlers are properly connected"""
        # This test ensures that our signal handlers are registered
        # We can test this by checking if they're in the signal registry
        
        # Get all signal handlers for post_save on Message model
        message_handlers = post_save.receivers
        handler_names = [handler[1].__name__ for handler in message_handlers 
                        if hasattr(handler[1], '__name__')]
        
        # Verify our handlers are registered
        self.assertIn('create_message_notification', handler_names)
        self.assertIn('update_conversation_timestamp', handler_names)
    
    @override_settings(DEBUG=True)
    def test_notification_creation_with_debug_logging(self):
        """Test notification creation with debug logging enabled"""
        user1 = User.objects.create_user(username='test1', password='pass')
        user2 = User.objects.create_user(username='test2', password='pass')
        
        conversation = Conversation.objects.create(created_by=user1)
        conversation.participants.add(user1, user2)
        
        # Capture print output from signal handlers
        with patch('builtins.print') as mock_print:
            message = Message.objects.create(
                sender=user1,
                conversation=conversation,
                message_body="Test message"
            )
            
            # Verify debug logging was called
            mock_print.assert_called()
            
            # Check if the correct log message was printed
            call_args_list = [call[0][0] for call in mock_print.call_args_list]
            notification_logs = [log for log in call_args_list if 'notifications for message' in log]
            self.assertTrue(len(notification_logs) > 0)


class EdgeCaseTests(TestCase):
    """
    Test edge cases and error scenarios.
    """
    
    def test_notification_for_empty_conversation(self):
        """Test notification creation for conversation with no other participants"""
        user = User.objects.create_user(username='lonely', password='pass')
        
        # Create conversation with only one participant
        conversation = Conversation.objects.create(created_by=user)
        conversation.participants.add(user)
        
        initial_count = Notification.objects.count()
        
        # Create message
        message = Message.objects.create(
            sender=user,
            conversation=conversation,
            message_body="Talking to myself"
        )
        
        # No notifications should be created
        self.assertEqual(Notification.objects.count(), initial_count)
    
    def test_long_message_content_truncation(self):
        """Test that long message content is properly truncated in notifications"""
        user1 = User.objects.create_user(username='sender', password='pass')
        user2 = User.objects.create_user(username='receiver', password='pass')
        
        conversation = Conversation.objects.create(created_by=user1)
        conversation.participants.add(user1, user2)
        
        # Create a very long message
        long_message = "A" * 500  # 500 characters
        
        message = Message.objects.create(
            sender=user1,
            conversation=conversation,
            message_body=long_message
        )
        
        # Get the created notification
        notification = Notification.objects.latest('created_at')
        
        # Verify content is truncated
        self.assertLess(len(notification.content), len(long_message))
        self.assertIn("...", notification.content)
    
    def test_notification_with_deleted_sender(self):
        """Test notification behavior when sender is deleted"""
        user1 = User.objects.create_user(username='sender', password='pass')
        user2 = User.objects.create_user(username='receiver', password='pass')
        
        conversation = Conversation.objects.create(created_by=user1)
        conversation.participants.add(user1, user2)
        
        # Create message and notification
        message = Message.objects.create(
            sender=user1,
            conversation=conversation,
            message_body="Test message"
        )
        
        notification = Notification.objects.latest('created_at')
        self.assertEqual(notification.sender, user1)
        
        # Delete the sender
        user1.delete()
        
        # Notification should still exist but sender should be None
        notification.refresh_from_db()
        self.assertIsNone(notification.sender)