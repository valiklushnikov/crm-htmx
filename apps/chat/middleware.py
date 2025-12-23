"""WebSocket JWT Authentication Middleware"""
import logging
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from datetime import datetime, timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


@database_sync_to_async
def get_user_from_token(token):
    """Получить пользователя из JWT токена"""
    try:
        validated_token = AccessToken(token)
        user_id = validated_token['user_id']
        user = User.objects.get(id=user_id)
        return user
    except (InvalidToken, TokenError) as e:
        logger.debug(f"Invalid access token in WebSocket: {e}")
        return None
    except User.DoesNotExist:
        logger.warning(f"User not found for WebSocket token")
        return None


@database_sync_to_async
def refresh_token_if_needed(refresh_token_str):
    """Обновить access токен если refresh токен валидный"""
    try:
        refresh = RefreshToken(refresh_token_str)
        new_access_token = str(refresh.access_token)
        user_id = refresh['user_id']
        user = User.objects.get(id=user_id)
        return user, new_access_token
    except (InvalidToken, TokenError) as e:
        logger.debug(f"Invalid refresh token in WebSocket: {e}")
        return None, None
    except User.DoesNotExist:
        logger.warning(f"User not found for refresh token")
        return None, None


class JWTAuthMiddleware:
    """
    Middleware для аутентификации WebSocket соединений через JWT из cookies
    с автоматическим обновлением токена
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Получаем cookies из headers
        headers = dict(scope.get('headers', []))
        cookie_header = headers.get(b'cookie', b'').decode()

        # Парсим cookies
        cookies = {}
        if cookie_header:
            for cookie in cookie_header.split('; '):
                if '=' in cookie:
                    key, value = cookie.split('=', 1)
                    cookies[key] = value

        # Получаем токены из cookies
        access_token = cookies.get('access_token')
        refresh_token = cookies.get('refresh_token')

        # Логируем для отладки
        if not access_token:
            logger.debug("No access_token in cookies for WebSocket connection")

        # Если токена нет в cookies, проверяем query string
        if not access_token:
            query_string = scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            access_token = query_params.get('token', [None])[0]

        # Аутентифицируем пользователя
        user = None
        if access_token:
            user = await get_user_from_token(access_token)

        # Если access токен невалидный, пробуем обновить через refresh
        if not user and refresh_token:
            logger.debug("Access token invalid, trying to refresh...")
            user, new_access_token = await refresh_token_if_needed(refresh_token)
            if user and new_access_token:
                logger.debug(
                    f"Token refreshed for user {user.email} in WebSocket")
                # Сохраняем новый токен для возможного использования
                scope['new_access_token'] = new_access_token

        if user:
            logger.debug("WebSocket authenticated user: %s", user.email)
            scope['user'] = user
        else:
            logger.debug("WebSocket authentication failed")
            scope['user'] = AnonymousUser()

        return await self.app(scope, receive, send)
