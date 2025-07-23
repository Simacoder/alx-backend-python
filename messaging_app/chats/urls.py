# chats/urls.py
from django.urls import path, include
from rest_framework_nested.routers import NestedDefaultRouter
from rest_framework import routers
from . import views

# Main router
router = routers.DefaultRouter()
router.register(r'conversations', views.ConversationViewSet, basename='conversation')
router.register(r'users', views.UserViewSet, basename='user')

# Nested router: messages under conversations
conversations_router = NestedDefaultRouter(router, r'conversations', lookup='conversation')
conversations_router.register(r'messages', views.MessageViewSet, basename='conversation-messages')

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('auth/profile/', views.UserProfileView.as_view(), name='user-profile'),

    # RESTful ViewSet routes
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),

    # Function-based view endpoints
    path('stats/', views.conversation_statistics, name='conversation-stats'),
    path('recent/', views.recent_conversations, name='recent-conversations'),
]
