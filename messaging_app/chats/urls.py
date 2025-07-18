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
    path('', include(router.urls)),
    path('', include(conversations_router.urls)),

    # Additional function-based view endpoints
    path('stats/', views.conversation_stats, name='conversation-stats'),
    path('recent/', views.recent_conversations, name='recent-conversations'),
]
