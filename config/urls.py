from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("api/", include("apps.templates_engine.api")),
    path("", include("apps.templates_engine.institution_urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("templates/", include("apps.templates_engine.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL + "profile_photos/", document_root=settings.MEDIA_ROOT / "profile_photos"
    )
