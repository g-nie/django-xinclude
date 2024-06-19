from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import SystemCheckError
from django.test import SimpleTestCase, override_settings


class CheckTests(SimpleTestCase):
    @override_settings(XINCLUDE_CACHE_TIMEOUT=0)
    def test_cache_timeout_0(self):
        message = (
            "(django_xinclude.E001) XINCLUDE_CACHE_TIMEOUT setting "
            "should be greater than 0."
        )
        with self.assertRaisesMessage(SystemCheckError, message):
            call_command("check")

    @override_settings(
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
        },
        XINCLUDE_CACHE_ALIAS="other",
    )
    def test_invalid_cache_alias(self):
        message = '(django_xinclude.E002) Cache alias "other" not found in CACHES.'
        with self.assertRaisesMessage(SystemCheckError, message):
            call_command("check")
