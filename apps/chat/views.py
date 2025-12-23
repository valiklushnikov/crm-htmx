from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Message, GroupMessage
from django.db.models import Q, Count, Max
from django.http import JsonResponse

User = get_user_model()

@login_required
def chat_view(request):
    users = User.objects.exclude(id=request.user.id)
    return render(request, "chat/chat.html", {"users": users})

@login_required
def get_messages(request, user_id):
    messages = Message.objects.filter(
        (Q(sender=request.user, receiver_id=user_id) |
         Q(sender_id=user_id, receiver=request.user))
    ).order_by("timestamp")

    data = {
        "messages": [
            {
                "sender": m.sender_id,
                "message": m.text,
                "timestamp": m.timestamp.isoformat(),
                "file": bool(m.file),
                "file_name": m.file_name if m.file else None,
                "file_url": m.file.url if m.file else None,
                "file_size": m.get_file_size_display() if m.file else None,
            } for m in messages
        ]
    }
    return JsonResponse(data)


@login_required
def get_group_messages(request):
    messages = GroupMessage.objects.all().order_by("timestamp")
    
    data = {
        "messages": [
            {
                "sender": m.sender_id,
                "sender_name": f"{m.sender.first_name} {m.sender.last_name}",
                "message": m.text,
                "timestamp": m.timestamp.isoformat(),
                "file": bool(m.file),
                "file_name": m.file_name if m.file else None,
                "file_url": m.file.url if m.file else None,
                "file_size": m.get_file_size_display() if m.file else None,
            } for m in messages
        ]
    }
    
    return JsonResponse(data)


@login_required
def get_unread_counts(request):
    """
    Получить информацию о последних сообщениях для синхронизации счетчика.
    Возвращает последнее сообщение от каждого пользователя с timestamp.
    Клиент сам определит, какие сообщения он уже видел.
    """
    from django.db.models import Max
    
    # Получаем последнее сообщение от каждого отправителя
    last_messages = Message.objects.filter(
        receiver=request.user
    ).values('sender_id').annotate(
        last_timestamp=Max('timestamp'),
        count=Count('id')
    )
    
    # Формируем данные для клиента
    result = {}
    for item in last_messages:
        result[str(item['sender_id'])] = {
            'last_timestamp': item['last_timestamp'].isoformat(),
            'total_count': item['count']
        }
    
    # Для группового чата получаем последнее сообщение
    last_group_msg = GroupMessage.objects.order_by('-timestamp').first()
    if last_group_msg:
        result['group'] = {
            'last_timestamp': last_group_msg.timestamp.isoformat(),
            'total_count': GroupMessage.objects.count()
        }
    else:
        result['group'] = {
            'last_timestamp': None,
            'total_count': 0
        }
    
    return JsonResponse(result)