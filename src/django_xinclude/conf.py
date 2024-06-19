from __future__ import annotations

from django.conf import settings


class Settings:
    @property
    def XINCLUDE_CACHE_ALIAS(self) -> str:  # noqa: N802
        return getattr(settings, "XINCLUDE_CACHE_ALIAS", "default")

    @property
    def XINCLUDE_CACHE_TIMEOUT(self) -> int | None:  # noqa: N802
        # The number of seconds the value should be stored in the cache.
        # If the setting is not present, Django will use the default timeout
        # argument of the appropriate backend in the CACHES setting.
        return getattr(settings, "XINCLUDE_CACHE_TIMEOUT", None)

    @property
    def XINCLUDE_SYNC_REQUEST_ATTR(self) -> str:  # noqa: N802
        return getattr(settings, "XINCLUDE_SYNC_REQUEST_ATTR", "xinclude_sync")


conf = Settings()
