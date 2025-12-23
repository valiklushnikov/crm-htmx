from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('messages/<int:user_id>/', views.get_messages, name='get_messages'),
    path('group-messages/', views.get_group_messages, name='get_group_messages'),
    path('unread-counts/', views.get_unread_counts, name='get_unread_counts'),
]
