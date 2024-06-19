from __future__ import annotations

import pickle
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from django.core.cache import caches

from django_xinclude import logger
from django_xinclude.conf import conf
from django_xinclude.exceptions import FragmentNotFoundError

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser, AnonymousUser
    from django.core.cache.backends.base import BaseCache


class ContextCache:
    @property
    def cache(self) -> BaseCache:
        return caches[conf.XINCLUDE_CACHE_ALIAS]

    def get_pickled_context(
        self, ctx: dict[str, Any], fragment_id: str
    ) -> dict[str, Any]:
        """Iterates over ``ctx`` to discard unpickable elements."""
        safe_ctx = {}
        discarded = []
        for k, v in ctx.items():
            try:
                pickle.dumps(v)
            except (pickle.PicklingError, TypeError):
                discarded.append(k)
            else:
                safe_ctx[k] = v
        if discarded:
            logger.debug(
                "The values for the following keys could not get pickled "
                f"and thus were not stored in cache (fragment_id: {fragment_id}): "
                f"{discarded}"
            )
        return safe_ctx

    def set(self, key: str, val: dict[str, Any]) -> None:
        """
        Sets the cache ``key`` to ``val``.

        It uses the ``XINCLUDE_CACHE_TIMEOUT`` setting if specified,
        otherwise Django will use the timeout argument of the appropriate backend
        in the CACHES setting.
        """
        if conf.XINCLUDE_CACHE_TIMEOUT is not None:
            set_kwargs = {"timeout": conf.XINCLUDE_CACHE_TIMEOUT}
        else:
            set_kwargs = {}
        self.cache.set(key, val, **set_kwargs)

    def get(self, key: str) -> FragmentData:
        data = self.cache.get(key)
        if data is None:
            raise FragmentNotFoundError()
        return FragmentData(meta=data["meta"], context=data["context"])


@dataclass
class FragmentData:
    meta: dict[str, Any]
    context: dict[str, Any]

    def __post_init__(self) -> None:
        self.user: AbstractUser | AnonymousUser | None = self.meta.get("user")
        self.template_names: list[str] = self.meta["template_names"]


ctx_cache = ContextCache()
