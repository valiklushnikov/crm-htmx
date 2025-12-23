from apps.main.models import Task
from apps.notification.models import Notification

def available_tasks(request):
    if request.user.is_authenticated and request.user.is_superuser:
        tasks = Task.objects.filter(status="completed")
        return {"available_tasks": tasks}

    if request.user.is_authenticated:
        tasks = Task.objects.filter(assigned_to=request.user)
        return {"available_tasks": tasks}
    return {"available_tasks": Task.objects.none()}


def expired_docs(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.all()
        return {"expired_docs": notifications}
    return {"expired_docs": Task.objects.none()}