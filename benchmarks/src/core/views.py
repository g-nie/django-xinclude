from __future__ import annotations

from django.contrib.auth.models import User
from django.views.generic import TemplateView


class ContextMixin:
    def get_context_data(self, **kwargs):
        data = super().get_context_data()
        data["unpickl"] = [lambda: None for _ in range(10000)]
        data["extra_context"] = {
            "strings": ["somevalue" for _ in range(10000)],
            "users": [User(username=f"user-{i}") for i in range(10000)],
        }
        return data


class XincludeView(ContextMixin, TemplateView):
    template_name = "core/home_xinclude.html"


class IncludeView(ContextMixin, TemplateView):
    template_name = "core/home_include.html"


class IncludePartialView(ContextMixin, TemplateView):
    template_name = "core/partials/partial.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data()
        data["extra"] = "hey"
        return data
