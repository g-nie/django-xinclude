from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("__debug__/", include("debug_toolbar.urls")),
    path("__xinclude__/", include("django_xinclude.urls")),
]
