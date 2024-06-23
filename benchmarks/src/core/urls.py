from __future__ import annotations

from core import views
from django.urls import path

urlpatterns = [
    path("xinclude/", views.XincludeView.as_view(), name="xinclude"),
    path("include/", views.IncludeView.as_view(), name="include"),
    path(
        "include-partial/", views.IncludePartialView.as_view(), name="include_partial"
    ),
]
