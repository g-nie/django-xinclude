from __future__ import annotations

from django.urls import include, path

from tests import views

urlpatterns = [
    path("__xinclude__/", include("django_xinclude.urls")),
    path("core/", views.CoreView.as_view(), name="core"),
    path("for_loop/", views.ForLoopView.as_view(), name="for_loop"),
]
