from django.conf import settings

def set_auth_cookies(response, access_token=None, refresh_token=None):
    is_dev = settings.DEBUG

    auth_options = {
        "httponly": True,
        "secure": not is_dev,
        "samesite": "Lax",
        "path": "/"
    }
    if access_token:
        response.set_cookie(
            key="access_token",
            value=access_token,
            **auth_options,
        )
    if refresh_token:
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            **auth_options,
        )

    return response
