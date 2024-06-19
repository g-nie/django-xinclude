from __future__ import annotations

from django.urls import path

from django_xinclude.views import XincludeView

app_name = "django_xinclude"

urlpatterns = [
    path("", XincludeView.as_view(), name="xinclude"),
]
