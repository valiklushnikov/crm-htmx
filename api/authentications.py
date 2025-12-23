from rest_framework.authentication import BaseAuthentication


class JWTCookieAuthentication(BaseAuthentication):
    def authenticate(self, request):
        user = getattr(request, 'jwt_user', None)
        if user and user.is_authenticated:
            return (user, None)
        return None