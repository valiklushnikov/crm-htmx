from django.urls import path
from .views import (
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
    CustomTokenRefreshView,
    UserProfileAPIView,
    employee_detail_api,
    employee_delete_api,
    TaskListCreateAPIView,
    TaskRetrieveUpdateDestroyAPIView,
    UserListAPIView,
    change_password_api
)

app_name = "api"

urlpatterns = [
    path("users/", UserListAPIView.as_view(), name="users_list"),
    path("register/", RegisterAPIView.as_view(), name="api_register"),
    path("login/", LoginAPIView.as_view(), name="api_login"),
    path("logout/", LogoutAPIView.as_view(), name="api_logout"),
    path("token/refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", UserProfileAPIView.as_view(), name="user_profile"),
    path("change-password/", change_password_api, name="change_password"),
    path("profile/<int:id>", employee_detail_api, name="profile"),
    path("profile/<int:id>/delete/", employee_delete_api, name="profile_delete"),
    path("tasks/", TaskListCreateAPIView.as_view(), name="task_list_create"),
    path(
        "tasks/<int:pk>/",
        TaskRetrieveUpdateDestroyAPIView.as_view(),
        name="task_detail",
    ),
]
