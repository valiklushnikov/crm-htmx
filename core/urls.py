from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('api/auth/', include('api.urls', namespace='api')),
    path("chat/", include("apps.chat.urls", namespace="chat")),
]


urlpatterns += i18n_patterns(
    # path("admin/", admin.site.urls),
    path("accounts/", include("apps.users.urls", namespace="accounts")),
    path("", include("apps.main.urls", namespace="main")),

)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
