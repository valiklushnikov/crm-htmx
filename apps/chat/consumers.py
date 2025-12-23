import json
import logging
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        logger.info(
            f"WebSocket connection attempt. User: {user}, Authenticated: {user.is_authenticated if user else 'No user'}")

        if not user or not user.is_authenticated:
            logger.warning(
                f"WebSocket connection rejected - user not authenticated")
            await self.close()
            return

        self.me = user.id
        self.other = self.scope["url_route"]["kwargs"]["user_id"]

        ids = sorted([self.me, int(self.other)])
        self.room_name = f"chat_{ids[0]}_{ids[1]}"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        logger.info(
            f"WebSocket connection accepted for user {self.me} to chat with {self.other}")

        self.heartbeat_task = asyncio.create_task(self.send_heartbeat())

    async def disconnect(self, close_code):
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': data.get('timestamp')
            }))
            return

        message_text = data.get("message")
        file_data = data.get("file")

        if not message_text and not file_data:
            return

        message_info = await self.save_message(self.me, self.other, message_text, file_data)

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "message": message_text or "",
                "sender": self.me,
                "file": message_info.get("file"),
                "file_name": message_info.get("file_name"),
                "file_url": message_info.get("file_url"),
            }
        )

    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, text, file_data):
        from django.contrib.auth import get_user_model
        from django.core.files.base import ContentFile
        import base64
        from .models import Message

        User = get_user_model()
        sender = User.objects.get(id=sender_id)
        receiver = User.objects.get(id=receiver_id)

        message = Message(
            sender=sender,
            receiver=receiver,
            text=text or ""
        )

        if file_data:
            file_content = base64.b64decode(file_data['content'])
            file_name = file_data['name']
            
            message.file.save(
                file_name,
                ContentFile(file_content),
                save=False
            )
            message.file_name = file_name
            message.file_size = len(file_content)

        message.save()

        return {
            "file": bool(message.file),
            "file_name": message.file_name if message.file else None,
            "file_url": message.file.url if message.file else None,
        }

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "file": event.get("file", False),
            "file_name": event.get("file_name"),
            "file_url": event.get("file_url"),
        }))

    async def send_heartbeat(self):
        """Отправляем heartbeat каждые 5 минут для поддержания соединения"""
        try:
            while True:
                await asyncio.sleep(300)  # 5 минут
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': asyncio.get_event_loop().time()
                }))
                logger.debug(f"Heartbeat sent to user {self.me}")
        except asyncio.CancelledError:
            logger.debug(f"Heartbeat cancelled for user {self.me}")
        except Exception as e:
            logger.error(f"Error in heartbeat for user {self.me}: {e}")


class GroupChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")

        logger.info(
            f"GroupChat WebSocket connection attempt. User: {user}, Authenticated: {user.is_authenticated if user else 'No user'}")

        if not user or not user.is_authenticated:
            logger.warning(
                f"GroupChat WebSocket connection rejected - user not authenticated")
            await self.close()
            return

        self.user_id = user.id
        self.room_name = "group_chat"

        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()
        logger.info(
            f"GroupChat WebSocket connection accepted for user {self.user_id}")

        self.heartbeat_task = asyncio.create_task(self.send_heartbeat())

    async def disconnect(self, close_code):
        # Отменяем heartbeat задачу
        if hasattr(self, 'heartbeat_task'):
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        if hasattr(self, 'room_name'):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': data.get('timestamp')
            }))
            return

        message_text = data.get("message")
        file_data = data.get("file")

        if not message_text and not file_data:
            return

        message_info = await self.save_group_message(self.user_id, message_text, file_data)

        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "group.message",
                "message": message_text or "",
                "sender": self.user_id,
                "sender_name": message_info["sender_name"],
                "file": message_info.get("file"),
                "file_name": message_info.get("file_name"),
                "file_url": message_info.get("file_url"),
            }
        )

    @database_sync_to_async
    def save_group_message(self, sender_id, text, file_data):
        from django.contrib.auth import get_user_model
        from django.core.files.base import ContentFile
        import base64
        from .models import GroupMessage

        User = get_user_model()
        sender = User.objects.get(id=sender_id)

        message = GroupMessage(
            sender=sender,
            text=text or ""
        )

        if file_data:
            file_content = base64.b64decode(file_data['content'])
            file_name = file_data['name']
            
            message.file.save(
                file_name,
                ContentFile(file_content),
                save=False
            )
            message.file_name = file_name
            message.file_size = len(file_content)

        message.save()

        return {
            "sender_name": f"{sender.first_name} {sender.last_name}",
            "file": bool(message.file),
            "file_name": message.file_name if message.file else None,
            "file_url": message.file.url if message.file else None,
        }

    async def group_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
            "sender_name": event["sender_name"],
            "file": event.get("file", False),
            "file_name": event.get("file_name"),
            "file_url": event.get("file_url"),
        }))

    async def send_heartbeat(self):
        """Отправляем heartbeat каждые 5 минут для поддержания соединения"""
        try:
            while True:
                await asyncio.sleep(300)  # 5 минут
                await self.send(text_data=json.dumps({
                    'type': 'heartbeat',
                    'timestamp': asyncio.get_event_loop().time()
                }))
                logger.debug(
                    f"Heartbeat sent to group chat user {self.user_id}")
        except asyncio.CancelledError:
            logger.debug(
                f"Heartbeat cancelled for group chat user {self.user_id}")
        except Exception as e:
            logger.error(
                f"Error in heartbeat for group chat user {self.user_id}: {e}")
