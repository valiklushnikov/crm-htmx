from django.contrib.auth import get_user_model

def chat_users(request):
    if not request.user.is_authenticated:
        return {"chat_users": []}

    User = get_user_model()
    return {
        "chat_users": User.objects.exclude(id=request.user.id)
    }