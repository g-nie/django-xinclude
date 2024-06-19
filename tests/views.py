from __future__ import annotations

from django.views.generic import TemplateView


class CoreView(TemplateView):
    template_name = "tests/core.html"


class ForLoopView(TemplateView):
    template_name = "tests/for_loop.html"
