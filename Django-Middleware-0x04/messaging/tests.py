from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db.models.signals import post_save, post_delete, pre_save
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock
import logging

from .models import Message, Notification
from .signals import (
    create_message_notification, 
    log_message_activity,
    prevent_self_messaging,
    cleanup_message_notifications
)


class MessageModelTest(TestCase):
    """Test cases for the Message model."""
    
    def setUp(self):
        """Set up test data."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            email='receiver@example.com',
            password='testpass123'
        )
    
    def test_message_creation(self):
        """Test creating a new message."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Hello, this is a test message!"
        )
        
        self.assertEqual(message.sender, self.sender)
        self.assertEqual(message.receiver, self.receiver)
        self.assertEqual(message.content, "Hello, this is a test message!")
        self.assertFalse(message.is_read)
        self.assertIsNotNone(message.timestamp)
    
    def test_message_str_representation(self):
        """Test the string representation of a message."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test message"
        )
        
        expected_str = f"Message from {self.sender.username} to {self.receiver.username}"
        self.assertEqual(str(message), expected_str)
    
    def test_mark_as_read(self):
        """Test marking a message as read."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test message"
        )
        
        self.assertFalse(message.is_read)
        message.mark_as_read()
        self.assertTrue(message.is_read)
    
    def test_message_ordering(self):
        """Test that messages are ordered by timestamp (newest first)."""
        message1 = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="First message"
        )
        message2 = Message.objects.create(
            sender=self.receiver,
            receiver=self.sender,
            content="Second message"
        )
        
        messages = Message.objects.all()
        self.assertEqual(messages[0], message2)  # Newest first
        self.assertEqual(messages[1], message1)


class NotificationModelTest(TestCase):
    """Test cases for the Notification model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
    
    def test_notification_creation(self):
        """Test creating a new notification."""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='message',
            title='Test Notification',
            content='This is a test notification'
        )
        
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'message')
        self.assertEqual(notification.title, 'Test Notification')
        self.assertFalse(notification.is_read)
    
    def test_create_message_notification_class_method(self):
        """Test the class method for creating message notifications."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.user,
            content="Hello there!"
        )
        
        notification = Notification.create_message_notification(message)
        
        self.assertEqual(notification.user, message.receiver)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(message.sender.username, notification.title)
        self.assertIn(message.content[:50], notification.content)
    
    def test_notification_str_representation(self):
        """Test the string representation of a notification."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Title',
            content='Test content'
        )
        
        expected_str = f"Notification for {self.user.username}: Test Title"
        self.assertEqual(str(notification), expected_str)
    
    def test_mark_as_read(self):
        """Test marking a notification as read."""
        notification = Notification.objects.create(
            user=self.user,
            title='Test Notification',
            content='Test content'
        )
        
        self.assertFalse(notification.is_read)
        notification.mark_as_read()
        self.assertTrue(notification.is_read)


class SignalTest(TestCase):
    """Test cases for Django signals."""
    
    def setUp(self):
        """Set up test data."""
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            email='receiver@example.com',
            password='testpass123'
        )
    
    def test_notification_created_on_message_save(self):
        """Test that a notification is created when a new message is saved."""
        initial_notification_count = Notification.objects.count()
        
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test message for signal"
        )
        
        # Check that a notification was created
        self.assertEqual(Notification.objects.count(), initial_notification_count + 1)
        
        # Check notification details
        notification = Notification.objects.latest('created_at')
        self.assertEqual(notification.user, self.receiver)
        self.assertEqual(notification.message, message)
        self.assertEqual(notification.notification_type, 'message')
        self.assertIn(self.sender.username, notification.title)
    
    def test_no_notification_on_message_update(self):
        """Test that no new notification is created when updating an existing message."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Original content"
        )
        
        initial_notification_count = Notification.objects.count()
        
        # Update the message
        message.content = "Updated content"
        message.save()
        
        # No new notification should be created
        self.assertEqual(Notification.objects.count(), initial_notification_count)
    
    def test_prevent_self_messaging_signal(self):
        """Test that the signal prevents users from messaging themselves."""
        with self.assertRaises(ValueError) as context:
            Message.objects.create(
                sender=self.sender,
                receiver=self.sender,  # Same as sender
                content="This should fail"
            )
        
        self.assertIn("cannot send messages to themselves", str(context.exception))
    
    def test_cleanup_notifications_on_message_delete(self):
        """Test that related notifications are deleted when a message is deleted."""
        message = Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Message to be deleted"
        )
        
        # Verify notification was created
        self.assertEqual(Notification.objects.filter(message=message).count(), 1)
        
        # Delete the message
        message.delete()
        
        # Verify related notifications were cleaned up
        self.assertEqual(Notification.objects.filter(message=message).count(), 0)
    
    @patch('messaging.signals.logger')
    def test_message_activity_logging(self, mock_logger):
        """Test that message activities are properly logged."""
        Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test logging"
        )
        
        # Verify that info logging was called
        mock_logger.info.assert_called()
        log_calls = mock_logger.info.call_args_list
        
        # Check that at least one call contains message creation info
        logged_message_creation = any(
            "New message created" in str(call) for call in log_calls
        )
        self.assertTrue(logged_message_creation)
    
    @override_settings(EMAIL_NOTIFICATIONS_ENABLED=True)
    @patch('messaging.signals.send_mail')
    def test_email_notification_sending(self, mock_send_mail):
        """Test that email notifications are sent when enabled."""
        Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test email notification"
        )
        
        # Verify send_mail was called
        mock_send_mail.assert_called_once()
        
        # Check the arguments passed to send_mail
        call_args = mock_send_mail.call_args
        self.assertIn(self.sender.username, call_args[1]['subject'])
        self.assertEqual(call_args[1]['recipient_list'], [self.receiver.email])


class SignalDisconnectionTest(TestCase):
    """Test signal disconnection for testing purposes."""
    
    def setUp(self):
        """Set up test data and disconnect signals."""
        # Disconnect signals to prevent side effects during testing
        post_save.disconnect(create_message_notification, sender=Message)
        
        self.sender = User.objects.create_user(
            username='sender',
            password='testpass123'
        )
        self.receiver = User.objects.create_user(
            username='receiver',
            password='testpass123'
        )
    
    def tearDown(self):
        """Reconnect signals after testing."""
        # Reconnect signals after test
        post_save.connect(create_message_notification, sender=Message)
    
    def test_no_notification_when_signal_disconnected(self):
        """Test that no notification is created when signal is disconnected."""
        initial_notification_count = Notification.objects.count()
        
        Message.objects.create(
            sender=self.sender,
            receiver=self.receiver,
            content="Test message without signal"
        )
        
        # No notification should be created since signal is disconnected
        self.assertEqual(Notification.objects.count(), initial_notification_count)


class MessageQueryTest(TestCase):
    """Test cases for Message model queries and related names."""
    
    def setUp(self):
        """Set up test data."""
        self.user1 = User.objects.create_user(
            username='user1',
            email='user1@example.com',
            password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='user2',
            email='user2@example.com',
            password='testpass123'
        )
        self.user3 = User.objects.create_user(
            username='user3',
            email='user3@example.com',
            password='testpass123'
        )
    
    def test_sent_messages_related_name(self):
        """Test the sent_messages related name on User model."""
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Message 1"
        )
        Message.objects.create(
            sender=self.user1,
            receiver=self.user3,
            content="Message 2"
        )
        
        sent_messages = self.user1.sent_messages.all()
        self.assertEqual(sent_messages.count(), 2)
    
    def test_received_messages_related_name(self):
        """Test the received_messages related name on User model."""
        Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Message 1"
        )
        Message.objects.create(
            sender=self.user3,
            receiver=self.user2,
            content="Message 2"
        )
        
        received_messages = self.user2.received_messages.all()
        self.assertEqual(received_messages.count(), 2)
    
    def test_notifications_related_name(self):
        """Test the notifications related name on User model."""
        message = Message.objects.create(
            sender=self.user1,
            receiver=self.user2,
            content="Test message"
        )
        
        # Check that notification was created via signal
        notifications = self.user2.notifications.all()
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first().message, message)


class NotificationQueryTest(TestCase):
    """Test cases for Notification model queries."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.sender = User.objects.create_user(
            username='sender',
            email='sender@example.com',
            password='testpass123'
        )
    
    def test_unread_notifications_filter(self):
        """Test filtering unread notifications."""
        # Create some notifications
        Notification.objects.create(
            user=self.user,
            title='Unread 1',
            content='Content 1',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            title='Read 1',
            content='Content 2',
            is_read=True
        )
        Notification.objects.create(
            user=self.user,
            title='Unread 2',
            content='Content 3',
            is_read=False
        )
        
        unread_notifications = Notification.objects.filter(
            user=self.user,
            is_read=False
        )
        self.assertEqual(unread_notifications.count(), 2)
    
    def test_notification_ordering(self):
        """Test that notifications are ordered by created_at (newest first)."""
        notification1 = Notification.objects.create(
            user=self.user,
            title='First',
            content='First notification'
        )
        notification2 = Notification.objects.create(
            user=self.user,
            title='Second',
            content='Second notification'
        )
        
        notifications = Notification.objects.filter(user=self.user)
        self.assertEqual(notifications[0], notification2)  # Newest first
        self.assertEqual(notifications[1], notification1)


class IntegrationTest(TestCase):
    """Integration tests for the complete messaging system."""
    
    def setUp(self):
        """Set up test data."""
        self.alice = User.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        self.bob = User.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        self.charlie = User.objects.create_user(
            username='charlie',
            email='charlie@example.com',
            password='testpass123'
        )
    
    def test_complete_messaging_flow(self):
        """Test the complete flow from message creation to notification."""
        # Alice sends a message to Bob
        message = Message.objects.create(
            sender=self.alice,
            receiver=self.bob,
            content="Hello Bob, how are you?"
        )
        
        # Check that Bob received a notification
        bob_notifications = Notification.objects.filter(user=self.bob)
        self.assertEqual(bob_notifications.count(), 1)
        
        notification = bob_notifications.first()
        self.assertEqual(notification.message, message)
        self.assertIn('alice', notification.title.lower())
        self.assertFalse(notification.is_read)
        
        # Bob marks the notification as read
        notification.mark_as_read()
        self.assertTrue(notification.is_read)
        
        # Bob marks the message as read
        message.mark_as_read()
        self.assertTrue(message.is_read)
    
    def test_multiple_users_messaging(self):
        """Test messaging between multiple users."""
        # Alice sends messages to Bob and Charlie
        Message.objects.create(
            sender=self.alice,
            receiver=self.bob,
            content="Hi Bob!"
        )
        Message.objects.create(
            sender=self.alice,
            receiver=self.charlie,
            content="Hi Charlie!"
        )
        
        # Bob sends a message to Charlie
        Message.objects.create(
            sender=self.bob,
            receiver=self.charlie,
            content="Hey Charlie, did you see Alice's message?"
        )
        
        # Check notification counts
        self.assertEqual(Notification.objects.filter(user=self.bob).count(), 1)
        self.assertEqual(Notification.objects.filter(user=self.charlie).count(), 2)
        self.assertEqual(Notification.objects.filter(user=self.alice).count(), 0)
    
    def test_message_deletion_cascades_notifications(self):
        """Test that deleting a message also deletes related notifications."""
        message = Message.objects.create(
            sender=self.alice,
            receiver=self.bob,
            content="This message will be deleted"
        )
        
        # Verify notification was created
        self.assertEqual(Notification.objects.filter(message=message).count(), 1)
        
        # Delete the message
        message_id = message.id
        message.delete()
        
        # Verify notification was also deleted
        self.assertEqual(Notification.objects.filter(message_id=message_id).count(), 0)


class EdgeCaseTest(TestCase):
    """Test edge cases and error conditions."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_empty_message_content(self):
        """Test creating a message with empty content."""
        message = Message.objects.create(
            sender=self.user,
            receiver=self.user,
            content=""
        )
        # This should fail due to the self-messaging prevention signal
        # But we need to catch it since the signal raises ValueError
    
    def test_very_long_message_content(self):
        """Test creating a message with very long content."""
        long_content = "A" * 1000  # Maximum allowed length
        
        message = Message.objects.create(
            sender=self.user,
            receiver=User.objects.create_user('receiver', password='pass'),
            content=long_content
        )
        
        self.assertEqual(len(message.content), 1000)
        
        # Check that notification content is truncated appropriately
        notification = Notification.objects.filter(message=message).first()
        self.assertLessEqual(len(notification.content), 500)  # Based on model field limit
    
    def test_notification_content_truncation(self):
        """Test that notification content is properly truncated for long messages."""
        receiver = User.objects.create_user('receiver', password='pass')
        long_message_content = "This is a very long message content " * 10  # > 50 chars
        
        message = Message.objects.create(
            sender=self.user,
            receiver=receiver,
            content=long_message_content
        )
        
        notification = Notification.objects.filter(message=message).first()
        # Check that the notification content includes the truncation indicator
        self.assertIn("...", notification.content)


class PerformanceTest(TestCase):
    """Test performance-related aspects."""
    
    def setUp(self):
        """Set up test data."""
        self.users = []
        for i in range(10):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='testpass123'
            )
            self.users.append(user)
    
    def test_bulk_message_creation_signals(self):
        """Test that signals work correctly with bulk operations."""
        messages_to_create = []
        for i in range(5):
            messages_to_create.append(
                Message(
                    sender=self.users[0],
                    receiver=self.users[i + 1],
                    content=f"Bulk message {i}"
                )
            )
        
        # Note: bulk_create doesn't trigger signals in Django
        # So we create them individually to test signal behavior
        initial_notification_count = Notification.objects.count()
        
        for message_data in messages_to_create:
            Message.objects.create(
                sender=message_data.sender,
                receiver=message_data.receiver,
                content=message_data.content
            )
        
        # Should have created 5 notifications
        self.assertEqual(
            Notification.objects.count(),
            initial_notification_count + 5
        )