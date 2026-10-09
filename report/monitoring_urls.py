from django.urls import path

from .views import monitoring

urlpatterns = [
    path('chat/', monitoring.ChatList, name='mon_chat'),
    path('chat/<int:pk>/', monitoring.ChatDetail, name='mon_chat_detail'),
    path('pronunciation/', monitoring.PronList, name='mon_pron'),
]
