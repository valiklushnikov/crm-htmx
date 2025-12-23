from django.shortcuts import render, redirect
from functools import wraps


def jwt_login_required(view_func):
    """
    Декоратор для перевірки JWT аутентифікації в шаблонах
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login_page')
        return view_func(request, *args, **kwargs)
    return wrapper


def login_page(request):
    """Сторінка входу"""
    if request.user.is_authenticated:
        return redirect('main:dashboard')
    return render(request, 'users/accounts/login.html')


def register_page(request):
    """Сторінка реєстрації"""
    if request.user.is_authenticated:
        return redirect('main:dashboard')
    return render(request, 'users/accounts/register.html')
