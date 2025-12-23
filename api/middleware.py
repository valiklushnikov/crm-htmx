from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class JWTAuthenticationFromCookieMiddleware(MiddlewareMixin):
    """
    Middleware для аутентификации через JWT токен из cookies
    с автоматическим обновлением access token
    """

    REFRESH_THRESHOLD = timedelta(minutes=2)

    def process_request(self, request):

        if hasattr(request, 'user') and request.user.is_authenticated:
            return None

        access_token = request.COOKIES.get('access_token')
        refresh_token = request.COOKIES.get('refresh_token')

        if not access_token:
            auth_header = request.META.get('HTTP_AUTHORIZATION', '')
            if auth_header.startswith('Bearer '):
                access_token = auth_header.split(' ')[1]

        request._jwt_token_refreshed = False
        request._new_access_token = None

        if access_token:
            user = self._authenticate_with_token(access_token)

            if user:
                request.user = user
                request.jwt_user = user
            elif refresh_token:
                user, new_access_token = self._refresh_access_token(refresh_token)

                if user and new_access_token:
                    request.user = user
                    request.jwt_user = user
                    request._jwt_token_refreshed = True
                    request._new_access_token = new_access_token
                    logger.info(f"Access token refreshed for user {user.email}")
                else:
                    request.user = AnonymousUser()
            else:
                request.user = AnonymousUser()
        elif refresh_token:
            user, new_access_token = self._refresh_access_token(refresh_token)

            if user and new_access_token:
                request.user = user
                request.jwt_user = user
                request._jwt_token_refreshed = True
                request._new_access_token = new_access_token
                logger.info(f"Access token created from refresh for user {user.email}")
            else:
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()

        return None

    def process_response(self, request, response):
        """
        Устанавливаем новый access токен в cookie, если он был обновлен
        """
        if hasattr(request, '_jwt_token_refreshed') and request._jwt_token_refreshed:
            if hasattr(request, '_new_access_token') and request._new_access_token:
                response.set_cookie(
                    key='access_token',
                    value=request._new_access_token,
                    max_age=900,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    path='/'
                )
                logger.debug("New access token set in cookie")

        return response

    def _authenticate_with_token(self, token):
        """
        Аутентификация пользователя по access токену
        Возвращает User или None
        """
        try:
            validated_token = AccessToken(token)
            user_id = validated_token['user_id']

            exp_timestamp = validated_token['exp']
            exp_datetime = datetime.fromtimestamp(exp_timestamp)
            time_until_expiry = exp_datetime - datetime.now()

            if time_until_expiry < self.REFRESH_THRESHOLD:
                logger.debug(f"Access token expires soon ({time_until_expiry}), will refresh")

            user = User.objects.get(id=user_id)
            return user

        except (InvalidToken, TokenError) as e:
            logger.debug(f"Invalid access token: {e}")
            return None
        except User.DoesNotExist:
            logger.warning(f"User not found for token")
            return None

    def _refresh_access_token(self, refresh_token_str):
        """
        Обновление access токена через refresh токен
        Возвращает (User, new_access_token) или (None, None)
        """
        try:
            refresh = RefreshToken(refresh_token_str)

            user_id = refresh['user_id']
            user = User.objects.get(id=user_id)

            new_access_token = str(refresh.access_token)

            return user, new_access_token

        except (InvalidToken, TokenError) as e:
            logger.debug(f"Invalid refresh token: {e}")
            return None, None
        except User.DoesNotExist:
            logger.warning(f"User not found for refresh token")
            return None, None
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None, None
