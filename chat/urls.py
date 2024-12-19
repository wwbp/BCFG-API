from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('participant/<int:id>/incoming/',
         views.incoming_message, name='incoming_message'),
    path('chat/', views.chat_page_view, name='chat_page'),
    path('chat/login/', views.chat_login, name='login'),
    path('chat/user_info/', views.get_user_info, name='get_user_info'),
    path('chat/send/', views.chat_send_message, name='chat_send_message'),
    path('chat/get_conversation/', views.get_conversation, name='get_conversation'),
    path('prompt/', views.prompt_view, name='prompt'),
    path('activities/add/', views.activity_add, name='activity_add'),
    path('activities/<int:pk>/edit/', views.activity_edit, name='activity_edit'),
    path('activities/<int:pk>/delete/',
         views.activity_delete, name='activity_delete'),
    path('chat/restart_session/', views.restart_session, name='restart_session'),
]
