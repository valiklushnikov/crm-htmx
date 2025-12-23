from .utils import set_change_user


class CurrentUserMiddleware:
    """
    Middleware для сохранения текущего пользователя в thread-local переменную
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if hasattr(request, 'user') and request.user.is_authenticated:
            set_change_user(request.user)
        else:
            set_change_user(None)
        
        response = self.get_response(request)

        set_change_user(None)
        
        return response