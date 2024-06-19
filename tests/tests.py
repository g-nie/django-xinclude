from __future__ import annotations

import pickle
import re
import uuid
from io import TextIOWrapper
from typing import Any
from unittest import mock

from django.contrib.auth.models import AnonymousUser, User
from django.core.cache import caches
from django.core.cache.backends.redis import RedisCache
from django.http import HttpRequest
from django.template import engines
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    override_settings,
)
from django.urls import reverse
from django_xinclude.cache import ctx_cache


def get_include_html(fragment_id, primary_nodes=""):
    return (
        f"""<div hx-get="/__xinclude__/?fragment_id={fragment_id}"""
        """" hx-trigger="load once"\n     hx-swap="outerHTML">\n    """
        f"""{primary_nodes}\n</div>"""
    )


def request_mock(**kwargs: Any) -> mock.MagicMock:
    return mock.MagicMock(spec=HttpRequest, **kwargs)


class CacheTests(SimpleTestCase):
    def test_context_cache_alias_default(self):
        self.assertIs(ctx_cache.cache, caches["default"])

    @override_settings(
        CACHES={
            "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
            "redis": {"BACKEND": "django.core.cache.backends.redis.RedisCache"},
        },
        XINCLUDE_CACHE_ALIAS="redis",
    )
    def test_context_cache_alias_override(self):
        self.assertTrue(isinstance(ctx_cache.cache, RedisCache))

    @mock.patch("django_xinclude.cache.ContextCache.cache")
    def test_context_cache_timeout_default(self, cache):
        ctx_cache.set("foo", {})
        cache.set.assert_called_once_with("foo", {})  # no kwarg

    @override_settings(XINCLUDE_CACHE_TIMEOUT=100)
    @mock.patch("django_xinclude.cache.ContextCache.cache")
    def test_context_cache_timeout_set(self, cache):
        ctx_cache.set("foo", {})
        cache.set.assert_called_once_with("foo", {}, timeout=100)


class TemplateTagTests(SimpleTestCase):
    fragment_id: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fragment_id = str(uuid.uuid4())

    def setUp(self):
        super().setUp()
        node_klass = "django_xinclude.templatetags.xinclude.HtmxIncludeNode"
        fragment_patcher = mock.patch(
            f"{node_klass}.fragment_id",
            new_callable=mock.PropertyMock,
            return_value=self.fragment_id,
        )
        self.fragment = fragment_patcher.start()
        self.addCleanup(fragment_patcher.stop)
        cache_patcher = mock.patch("django_xinclude.cache.ContextCache.cache")
        self.cache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_xinclude(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" %}{% endxinclude %}
        """
        t = engines["django"].from_string(template)
        rendered = t.render({"request": request_mock()}).strip()
        self.assertEqual(rendered, get_include_html(self.fragment_id))

    def test_cache_context(self):
        template = """
        {% load xinclude %}
        {% with foo="bar" %}
        {% xinclude "tests/partials/hello.html" with zoo="car" %}{% endxinclude %}
        {% endwith %}
        """
        t = engines["django"].from_string(template)
        t.render({"request": request_mock()})
        self.cache.set.assert_called_once()
        fragment_id, ctx = self.cache.set.mock_calls[0].args
        self.assertEqual(fragment_id, self.fragment_id)
        self.assertTrue({"foo": "bar", "zoo": "car"}.items() <= ctx["context"].items())
        self.assertEqual(ctx["meta"]["template_names"], ["tests/partials/hello.html"])

    def test_skips_unpickable_objects(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" %}{% endxinclude %}
        """
        t = engines["django"].from_string(template)
        with mock.patch("django_xinclude.cache.logger") as logger:
            t.render({"a": mock.MagicMock(), "b": mock.MagicMock()})
        ctx = self.cache.set.mock_calls[0].args[1]["context"]
        self.assertNotIn("a", ctx)
        self.assertNotIn("b", ctx)
        logger.debug.assert_called_once_with(
            "The values for the following keys could not get pickled and thus were not "
            f"stored in cache (fragment_id: {self.fragment_id}): ['a', 'b']"
        )

    def test_pickling_typerror_is_tolerated(self):
        unp = TextIOWrapper(mock.MagicMock())
        self.assertRaises(TypeError, lambda: pickle.dumps(unp))
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" %}{% endxinclude %}
        """
        t = engines["django"].from_string(template)
        req = RequestFactory().get("")
        req.user = AnonymousUser()
        t.render({"request": req, "zoo": unp})
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertIn("user", ctx["meta"])
        self.assertNotIn("zoo", ctx)

    def test_context_only(self):
        template = """
        {% load xinclude %}
        {% with foo="bar" %}
        {% xinclude "tests/partials/hello.html" with zoo="car" only %}{% endxinclude %}
        {% endwith %}
        """
        t = engines["django"].from_string(template)
        t.render({"request": request_mock()})
        ctx = self.cache.set.mock_calls[0].args[1]["context"]
        self.assertEqual(ctx["zoo"], "car")
        self.assertNotIn("foo", ctx)

    def test_trigger_may_be_passed(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" hx-trigger="intersect once" %}
        {% endxinclude %}
        """
        t = engines["django"].from_string(template)
        self.assertIn(
            'hx-trigger="intersect once"', t.render({"request": request_mock()})
        )

    def test_hx_vars_not_passed_to_cache(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" hx-trigger="intersect once" %}
        {% endxinclude %}
        """
        t = engines["django"].from_string(template)
        t.render({"request": request_mock()})
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertNotIn("hx_trigger", ctx)

    def test_with_and_trigger(self):
        template = (
            """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" """
            + """hx-trigger="intersect once" with foo="bar" %}{% endxinclude %}
        """
        )
        t = engines["django"].from_string(template)
        self.assertIn(
            'hx-trigger="intersect once"', t.render({"request": request_mock()})
        )
        self.cache.set.assert_called_once()
        ctx = self.cache.set.mock_calls[0].args[1]["context"]
        self.assertTrue({"foo": "bar"}.items() <= ctx.items())

    def test_only_and_trigger(self):
        template = (
            """
        {% load xinclude %}
        {% with foo="bar" %}
        {% xinclude "tests/partials/hello.html" """
            + """hx-trigger="intersect once" with zoo="car" only %}{% endxinclude %}
        {% endwith %}
        """
        )
        t = engines["django"].from_string(template)
        rendered = t.render({"request": request_mock()})
        self.assertIn('hx-trigger="intersect once"', rendered)
        self.cache.set.assert_called_once()
        ctx = self.cache.set.mock_calls[0].args[1]["context"]
        self.assertTrue({"zoo": "car"}.items() <= ctx.items())
        self.assertNotIn("foo", ctx.keys())

    def test_timing(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" swap-time="1s" settle-time="2s" %}
        {% endxinclude %}
        """
        t = engines["django"].from_string(template)
        self.assertIn(
            'hx-swap="outerHTML swap:1s settle:2s"',
            t.render({"request": request_mock()}),
        )

    def test_sync_include(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" hx-trigger="intersect once" %}
        {% endxinclude %}
        """
        t = engines["django"].from_string(template)
        rendered = t.render(request=mock.MagicMock(xinclude_sync=True)).strip()
        self.assertEqual(rendered, "Hello")

    def test_xinclude_template_variable(self):
        template = """
        {% load xinclude %}
        {% xinclude template_name %}{% endxinclude %}
        """
        t = engines["django"].from_string(template)
        rendered = t.render(
            {"template_name": "tests/partials/hello.html", "request": request_mock()}
        ).strip()
        self.assertEqual(rendered, get_include_html(self.fragment_id))

    def test_xinclude_template_variable_iterable(self):
        template = """
        {% load xinclude %}
        {% xinclude template_name %}{% endxinclude %}
        """
        t = engines["django"].from_string(template)
        rendered = t.render(
            {"template_name": ["tests/partials/hello.html"], "request": request_mock()}
        ).strip()
        self.assertEqual(rendered, get_include_html(self.fragment_id))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["template_names"], ["tests/partials/hello.html"])

    def test_for_loop_include(self):
        template = """
        {% load xinclude %}
        {% for i in "00" %}
            {% xinclude "tests/partials/hello.html" %}{% endxinclude %}
        {% endfor %}
        """
        self.fragment.side_effect = ["fr1", "fr2"]
        t = engines["django"].from_string(template)
        rendered = t.render({"request": request_mock()})
        fragment_ids = re.findall(r'\?fragment_id=([\w-]+)"', rendered)
        self.assertEqual(fragment_ids, ["fr1", "fr2"])

    def test_primary_nodes(self):
        template = """
        {% load xinclude %}
        {% xinclude "tests/partials/hello.html" %}
        <div class="custom">Processing</div>
        {% with foo="bar" %}<div>foo</div>{% endwith %}
        {% endxinclude %}
        """
        t = engines["django"].from_string(template)
        rendered = t.render({}).strip()
        pr_el = '<div class="custom">Processing</div>\n        <div>foo</div>'
        self.assertEqual(rendered, get_include_html(self.fragment_id, pr_el))


class ViewTests(SimpleTestCase):
    def setUp(self):
        super().setUp()
        self.anon = AnonymousUser()
        cache_patcher = mock.patch("django_xinclude.cache.ContextCache.cache")
        self.cache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_view_renders_passed_template(self):
        self.cache.get.return_value = {
            "meta": {
                "user": self.anon,
                "template_names": ["tests/partials/hello.html"],
            },
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertTemplateUsed(response, "tests/partials/hello.html")
        self.assertEqual(response.rendered_content, "Hello\n")  # type: ignore[attr-defined]

    def test_view_context(self):
        self.cache.get.return_value = {
            "meta": {
                "user": self.anon,
                "template_names": ["tests/partials/hello.html"],
            },
            "context": {"foo": "bar"},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.context_data, {"foo": "bar"})  # type: ignore[attr-defined]

    def test_missing_context(self):
        self.cache.get.return_value = None
        url = "/__xinclude__/?fragment_id=missing"
        with mock.patch("django_xinclude.views.logger") as logger:
            response = self.client.get(url)
        self.assertEqual(response.status_code, 500)
        logger.debug.assert_called_once_with("fragment_id: missing not found in cache.")

    def test_missing_meta(self):
        self.cache.get.return_value = {}
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_meta_user(self):
        self.cache.get.return_value = {
            "meta": {"template_names": ["tests/partials/hello.html"]},
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_fragment_id(self):
        url = "/__xinclude__/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_template_404(self):
        self.cache.get.return_value = {"meta": {"user": self.anon}, "context": {}}
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_only_1_fragment_id_allowed(self):
        self.cache.get.return_value = {"meta": {"user": self.anon}, "context": {}}
        url = "/__xinclude__/?fragment_id=abc123&fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_inexistent_template_404(self):
        self.cache.get.return_value = {
            "meta": {"user": self.anon, "template_names": ["inexistent"]},
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_missing_context_404(self):
        self.cache.get.return_value = {
            "meta": {"user": self.anon, "template_names": ["tests/partials/hello.html"]}
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_multiple_templates_inexistent_first(self):
        self.cache.get.return_value = {
            "meta": {
                "user": self.anon,
                "template_names": ["inexistent", "tests/partials/hello.html"],
            },
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertTemplateUsed(response, "tests/partials/hello.html")
        self.assertEqual(response.rendered_content, "Hello\n")  # type: ignore[attr-defined]

    def test_multiple_templates_inexistent_second(self):
        self.cache.get.return_value = {
            "meta": {
                "user": self.anon,
                "template_names": ["tests/partials/hello.html", "inexistent"],
            },
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertTemplateUsed(response, "tests/partials/hello.html")
        self.assertEqual(response.rendered_content, "Hello\n")  # type: ignore[attr-defined]


def get_templates_settings(context_processors: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": context_processors},
        }
    ]


class AuthTests(TestCase):
    def setUp(self):
        super().setUp()
        cache_patcher = mock.patch("django_xinclude.cache.ContextCache.cache")
        self.cache = cache_patcher.start()
        self.addCleanup(cache_patcher.stop)

    def test_tag_stores_authed_user_in_cache(self):
        user = User.objects.create()
        self.client.force_login(user)
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["user"], user)

    def test_tag_stores_anon_user_in_cache(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["user"], AnonymousUser())

    @override_settings(
        INSTALLED_APPS=["django.contrib.auth", "django_xinclude", "tests"],
        TEMPLATES=get_templates_settings(
            ["django.template.context_processors.request"]
        ),
    )
    def test_tag_store_user_minimal_processors_1(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["user"], AnonymousUser())

    @override_settings(
        INSTALLED_APPS=["django.contrib.auth", "django_xinclude", "tests"],
        TEMPLATES=get_templates_settings(
            ["django.contrib.auth.context_processors.auth"]
        ),
    )
    def test_tag_store_user_minimal_processors_2(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["user"], AnonymousUser())

    @override_settings(
        INSTALLED_APPS=["django_xinclude", "tests"],
        TEMPLATES=get_templates_settings(
            ["django.contrib.auth.context_processors.auth"]
        ),
        MIDDLEWARE=[],
    )
    def test_tag_store_user_minimal_processors_3(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertEqual(ctx["meta"]["user"], AnonymousUser())

    @override_settings(
        INSTALLED_APPS=["django_xinclude", "tests"],
        TEMPLATES=get_templates_settings([]),
        MIDDLEWARE=[],
    )
    def test_tag_may_not_store_user_1(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertNotIn("user", ctx["meta"])

    @override_settings(
        INSTALLED_APPS=["django_xinclude", "tests"],
        TEMPLATES=get_templates_settings(
            ["django.template.context_processors.request"]
        ),
        MIDDLEWARE=[],
    )
    def test_tag_may_not_store_user_2(self):
        self.client.get(reverse("core"))
        ctx = self.cache.set.mock_calls[0].args[1]
        self.assertNotIn("user", ctx["meta"])

    def test_view_404_for_different_user(self):
        self.cache.get.return_value = {
            "meta": {
                "user": mock.MagicMock(pk=10),
                "template_names": ["tests/partials/hello.html"],
            },
            "context": {},
        }
        user = User.objects.create(id=99)
        self.client.force_login(user)
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_view_200_for_same_user(self):
        user = User.objects.create(id=99)
        self.cache.get.return_value = {
            "meta": {"user": user, "template_names": ["tests/partials/hello.html"]},
            "context": {},
        }
        self.client.force_login(user)
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @override_settings(INSTALLED_APPS=["django_xinclude", "tests"], MIDDLEWARE=[])
    def test_view_cache_no_user(self):
        # If auth is disabled altogether, then we assume that
        # the user can access the view.
        self.cache.get.return_value = {
            "meta": {"template_names": ["tests/partials/hello.html"]},
            "context": {},
        }
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_cache_no_user_and_view_user(self):
        # Not sure if this can even happen, but we should raise 404 if it does.
        self.cache.get.return_value = {
            "meta": {"template_names": ["tests/partials/hello.html"]},
            "context": {},
        }
        user = User.objects.create(id=99)
        self.client.force_login(user)
        url = "/__xinclude__/?fragment_id=abc123"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
