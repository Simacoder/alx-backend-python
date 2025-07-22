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
                "messages": "/api/messages/"
            },
            "admin": "/admin/",
            "browsable_api": "/api-auth/login/"
        },
        "documentation": "Include 'Authorization: Bearer <token>' header for authenticated requests"
    })

"""
URL configuration for messaging_app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

urlpatterns = [
    # Root endpoint with API documentation
    path('', root_view, name='root'),
    
    # Admin interface
    path('admin/', admin.site.urls),
    
    # JWT Authentication endpoints
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # Main API endpoints (include your chats app URLs)
    path('api/', include('chats.urls')),
    
    # DRF browsable API authentication (for development/testing)
    path('api-auth/', include('rest_framework.urls')),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)