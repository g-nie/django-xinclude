from __future__ import annotations

from django.apps import AppConfig


class XincludeAppConfig(AppConfig):
    name = "django_xinclude"
    verbose_name = "django-xinclude"

    def ready(self) -> None:
        from django_xinclude import checks  # noqa: F401
