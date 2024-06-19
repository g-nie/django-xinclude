from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import Error, Tags, register

from django_xinclude.conf import conf

if TYPE_CHECKING:
    from django.core.checks.messages import CheckMessage


@register(Tags.compatibility)  # type: ignore[type-var]
def check_settings(
    app_configs: list[AppConfig] | None, **kwargs: Any
) -> list[CheckMessage]:
    checks: list[CheckMessage] = []
    if conf.XINCLUDE_CACHE_TIMEOUT == 0:
        msg = "XINCLUDE_CACHE_TIMEOUT setting should be greater than 0."
        checks.append(Error(msg, id="django_xinclude.E001"))
    if (alias := conf.XINCLUDE_CACHE_ALIAS) not in settings.CACHES:
        msg = f'Cache alias "{alias}" not found in CACHES.'
        checks.append(Error(msg, id="django_xinclude.E002"))
    return checks
