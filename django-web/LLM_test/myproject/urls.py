"""
URL configuration for myproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
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
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from chat import views as chat_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Аутентификация (синхронные view)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', chat_views.register, name='register'),
    path('password-reset/', chat_views.password_reset, name='password_reset'),

    # Основной чат (асинхронные view)
    path('', chat_views.chat_page, name='chat'),
    path('api/history/', chat_views.api_history, name='api_history'),
    path('send/', chat_views.send_message, name='send_message'),
]