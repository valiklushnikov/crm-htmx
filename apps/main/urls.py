from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),

    # HTMX endpoints
    path('employee/<int:employee_id>/', views.DashboardView.as_view(), name='employee_detail'),
    path('employee/form/', views.DashboardView.as_view(), name='employee_form'),
    path('employee/save/', views.DashboardView.as_view(), name='employee_save'),

    path('invites/', views.invites_for_register, name='invites'),
    path('tasks/', views.TasksBoardView.as_view(), name='tasks_board'),
    path('expired-docs/', views.expired_docs, name='expired_docs'),
    path('export-pdf/', views.export_employees_pdf, name='export_pdf'),
    path('lock-employee/', views.lock_employee, name='lock_employee'),
    path('unlock-employee/', views.unlock_employee, name='unlock_employee'),
    path('history/', views.HistoryListView.as_view(), name='history_list'),
]
