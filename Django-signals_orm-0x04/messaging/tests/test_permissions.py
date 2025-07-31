# chats/tests/test_permissions.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from chats.models import Conversation, Message, MessageReadStatus
from chats.permissions import (
    IsParticipantOfConversation,
    ConversationPermissions,
    MessagePermissions,
    IsAuthenticatedAndActive
)

User = get_user_model()


class PermissionTestCase(APITestCase):
    """
    Base test case with common setup for permission testing
    """
    
    def setUp(self):
        """
        Set up test users and authentication
        """
        # Create test users
        self.user1 = User.objects.create_user(
            username='testuser1',
            email='test1@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User1'
        )
        
        self.user2 = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User2'
        )
        
        self.user3 = User.objects.create_user(
            username='testuser3',
            email='test3@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User3'
        )
        
        # Create inactive user for testing
        self.inactive_user = User.objects.create_user(
            username='inactive',
            email='inactive@example.com',
            password='testpass123',
            is_active=False
        )
        
        # Set up API clients
        self.client1 = APIClient()
        self.client2 = APIClient()
        self.client3 = APIClient()
        self.anonymous_client = APIClient()
        
        # Generate JWT tokens and authenticate clients
        self.token1 = RefreshToken.for_user(self.user1)
        self.token2 = RefreshToken.for_user(self.user2)
        self.token3 = RefreshToken.for_user(self.user3)
        
        self.client1.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token1.access_token}')
        self.client2.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token2.access_token}')
        self.client3.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token3.access_token}')
    
    def create_conversation(self, created_by, participants=None, is_group=False):
        """
        Helper method to create a conversation
        """
        if participants is None:
            participants = [created_by]
        
        conversation = Conversation.objects.create(
            title=f"Test Conversation",
            created_by=created_by,
            is_group=is_group
        )
        conversation.participants.set(participants)
        return conversation
    
    def create_message(self, conversation, sender, content="Test message"):
        """
        Helper method to create a message
        """
        return Message.objects.create(
            conversation=conversation,
            sender=sender,
            content=content
        )


class AuthenticationPermissionTests(PermissionTestCase):
    """
    Test authentication requirements for API access
    """
    
    def test_anonymous_user_cannot_access_conversations(self):
        """
        Test that anonymous users cannot access conversation endpoints
        """
        response = self.anonymous_client.get('/api/conversations/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_anonymous_user_cannot_access_messages(self):
        """
        Test that anonymous users cannot access message endpoints
        """
        response = self.anonymous_client.get('/api/messages/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_inactive_user_cannot_access_api(self):
        """
        Test that inactive users cannot access the API
        """
        inactive_token = RefreshToken.for_user(self.inactive_user)
        inactive_client = APIClient()
        inactive_client.credentials(HTTP_AUTHORIZATION=f'Bearer {inactive_token.access_token}')
        
        response = inactive_client.get('/api/conversations/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_authenticated_user_can_access_api(self):
        """
        Test that authenticated active users can access the API
        """
        response = self.client1.get('/api/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ConversationPermissionTests(PermissionTestCase):
    """
    Test conversation access permissions
    """
    
    def test_user_can_only_see_their_conversations(self):
        """
        Test that users can only see conversations they participate in
        """
        # Create conversation with user1 and user2
        conversation1 = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # Create conversation with only user3
        conversation2 = self.create_conversation(
            created_by=self.user3,
            participants=[self.user3]
        )
        
        # User1 should only see conversation1
        response = self.client1.get('/api/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conversation_ids = [conv['conversation_id'] for conv in response.data['results']]
        self.assertIn(str(conversation1.conversation_id), conversation_ids)
        self.assertNotIn(str(conversation2.conversation_id), conversation_ids)
        
        # User3 should only see conversation2
        response = self.client3.get('/api/conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        conversation_ids = [conv['conversation_id'] for conv in response.data['results']]
        self.assertNotIn(str(conversation1.conversation_id), conversation_ids)
        self.assertIn(str(conversation2.conversation_id), conversation_ids)
    
    def test_non_participant_cannot_access_conversation(self):
        """
        Test that non-participants cannot access conversation details
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # User3 (not a participant) should not be able to access the conversation
        response = self.client3.get(f'/api/conversations/{conversation.conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_participant_can_access_conversation(self):
        """
        Test that participants can access conversation details
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # User1 (participant) should be able to access the conversation
        response = self.client1.get(f'/api/conversations/{conversation.conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User2 (participant) should be able to access the conversation
        response = self.client2.get(f'/api/conversations/{conversation.conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_only_creator_can_delete_conversation(self):
        """
        Test that only the conversation creator can delete it
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # User2 (participant but not creator) cannot delete
        response = self.client2.delete(f'/api/conversations/{conversation.conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # User1 (creator) can delete
        response = self.client1.delete(f'/api/conversations/{conversation.conversation_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_participants_can_update_conversation_title(self):
        """
        Test that participants can update conversation title
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2],
            is_group=True
        )
        
        # User2 (participant) can update title
        response = self.client2.patch(
            f'/api/conversations/{conversation.conversation_id}/update_title/',
            {'title': 'New Title'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_non_participant_cannot_add_participants(self):
        """
        Test that non-participants cannot add participants to group conversations
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2],
            is_group=True
        )
        
        # User3 (not a participant) cannot add participants
        response = self.client3.post(
            f'/api/conversations/{conversation.conversation_id}/add_participant/',
            {'user_id': self.user3.user_id}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class MessagePermissionTests(PermissionTestCase):
    """
    Test message access and modification permissions
    """
    
    def test_user_can_only_see_messages_from_their_conversations(self):
        """
        Test that users can only see messages from conversations they participate in
        """
        # Create conversation with user1 and user2
        conversation1 = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        message1 = self.create_message(conversation1, self.user1)
        
        # Create conversation with only user3
        conversation2 = self.create_conversation(
            created_by=self.user3,
            participants=[self.user3]
        )
        message2 = self.create_message(conversation2, self.user3)
        
        # User1 should only see message1
        response = self.client1.get('/api/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message_ids = [msg['message_id'] for msg in response.data['results']]
        self.assertIn(str(message1.message_id), message_ids)
        self.assertNotIn(str(message2.message_id), message_ids)
        
        # User3 should only see message2
        response = self.client3.get('/api/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message_ids = [msg['message_id'] for msg in response.data['results']]
        self.assertNotIn(str(message1.message_id), message_ids)
        self.assertIn(str(message2.message_id), message_ids)
    
    def test_only_sender_can_edit_message(self):
        """
        Test that only the message sender can edit their message
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        message = self.create_message(conversation, self.user1)
        
        # User2 (not the sender) cannot edit the message
        response = self.client2.patch(
            f'/api/messages/{message.message_id}/',
            {'content': 'Edited message'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # User1 (sender) can edit the message
        response = self.client1.patch(
            f'/api/messages/{message.message_id}/',
            {'content': 'Edited message'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_only_sender_can_delete_message(self):
        """
        Test that only the message sender can delete their message
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        message = self.create_message(conversation, self.user1)
        
        # User2 (not the sender) cannot delete the message
        response = self.client2.delete(f'/api/messages/{message.message_id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # User1 (sender) can delete the message
        response = self.client1.delete(f'/api/messages/{message.message_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
    
    def test_non_participant_cannot_send_message(self):
        """
        Test that non-participants cannot send messages to a conversation
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # User3 (not a participant) cannot send a message
        response = self.client3.post('/api/messages/', {
            'conversation': conversation.conversation_id,
            'content': 'Unauthorized message'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_participant_can_send_message(self):
        """
        Test that participants can send messages to a conversation
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        
        # User2 (participant) can send a message
        response = self.client2.post('/api/messages/', {
            'conversation': conversation.conversation_id,
            'content': 'Valid message'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_participant_can_mark_message_as_read(self):
        """
        Test that participants can mark messages as read (but not their own)
        """
        conversation = self.create_conversation(
            created_by=self.user1,
            participants=[self.user1, self.user2]
        )
        message = self.create_message(conversation, self.user1)
        
        # User2 (participant, not sender) can mark message as read
        response = self.client2.post(f'/api/messages/{message.message_id}/mark_as_read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # User1 (sender) cannot mark their own message as read
        response = self.client1.post(f'/api/messages/{message.message_id}/mark_as_read/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserSearchPermissionTests(PermissionTestCase):
    """
    Test user search and profile access permissions
    """
    
    def test_authenticated_user_can_search_users(self):
        """
        Test that authenticated users can search for other users
        """
        response = self.client1.get('/api/users/search/?q=test')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_anonymous_user_cannot_search_users(self):
        """
        Test that anonymous users cannot search for users
        """
        response = self.anonymous_client.get('/api/users/search/?q=test')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_user_can_access_own_profile(self):
        """
        Test that users can access their own profile
        """
        response = self.client1.get('/api/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user1.username)
    
    def test_user_can_view_other_users_basic_info(self):
        """
        Test that users can view other users' basic information for chat functionality
        """
        response = self.client1.get(f'/api/users/{self.user2.user_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class StatisticsPermissionTests(PermissionTestCase):
    """
    Test access to user statistics and conversation data
    """
    
    def test_user_can_access_own_statistics(self):
        """
        Test that users can access their own conversation statistics
        """
        response = self.client1.get('/api/conversation-statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('conversations', response.data)
        self.assertIn('messages', response.data)
    
    def test_user_can_access_recent_conversations(self):
        """
        Test that users can access their recent conversations
        """
        response = self.client1.get('/api/recent-conversations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_anonymous_user_cannot_access_statistics(self):
        """
        Test that anonymous users cannot access statistics
        """
        response = self.anonymous_client.get('/api/conversation-statistics/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


if __name__ == '__main__':
    import django
    django.setup()