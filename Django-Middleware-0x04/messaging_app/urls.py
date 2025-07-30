# messaging_app/urls.py
from django.http import JsonResponse
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

def root_view(request):
    return JsonResponse({
        "message": "Welcome to the Messaging API",
        "endpoints": {
            "api_root": "/api/",
            "authentication": {
                "login": "/api/auth/login/",
                "register": "/api/auth/register/",
                "refresh_token": "/api/auth/refresh/",
                "verify_token": "/api/auth/verify/",
                "profile": "/api/auth/profile/"
            },
            "messaging": {
                "conversations": "/api/conversations/",
                "messages": "/api/conversations/<id>/messages/"
            },
            "admin": "/admin/",
            "browsable_api": "/api-auth/login/"
        },
        "documentation": "Include 'Authorization: Bearer <token>' header for authenticated requests"
    })

urlpatterns = [
    # Root welcome endpoint
    path('', root_view, name='root'),

    # Admin interface
    path('admin/', admin.site.urls),

    # App routes (chats, users, conversations, etc.)
    path('api/', include('chats.urls')),

    # JWT authentication
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # DRF browsable API auth
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
