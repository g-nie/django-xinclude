from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.http import Http404, HttpResponseServerError
from django.template.exceptions import TemplateDoesNotExist
from django.template.loader import select_template
from django.views.generic import TemplateView

from django_xinclude import logger
from django_xinclude.cache import ctx_cache
from django_xinclude.exceptions import FragmentNotFoundError

if TYPE_CHECKING:
    from django.http.request import HttpRequest
    from django.http.response import HttpResponseBase


class XincludeView(TemplateView):
    def dispatch(
        self, request: HttpRequest, *args: Any, **kwargs: Any
    ) -> HttpResponseBase:
        try:
            fragment_id = request.GET["fragment_id"]
        except KeyError:
            raise Http404  # noqa: B904
        try:
            # noinspection PyAttributeOutsideInit
            self.fragment = ctx_cache.get(fragment_id)
        except (KeyError, TypeError):
            raise Http404  # noqa: B904
        except FragmentNotFoundError:
            logger.debug(f"fragment_id: {fragment_id} not found in cache.")
            return HttpResponseServerError()
        self.authorize_user()
        return super().dispatch(request, *args, **kwargs)

    def authorize_user(self) -> None:
        # The request user should be the one that initially accessed the parent view
        # (and added to cache), or AnonymousUser in both cases;
        # otherwise raise 404.
        try:
            if self.request.user != self.fragment.user:
                raise Http404
        except AttributeError:
            pass

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        return self.fragment.context

    def get_template_names(self) -> list[str]:
        try:
            select_template(self.fragment.template_names)
        except TemplateDoesNotExist:
            raise Http404  # noqa: B904
        return self.fragment.template_names
