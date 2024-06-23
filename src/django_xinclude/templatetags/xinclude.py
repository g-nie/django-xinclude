from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from django.template.base import FilterExpression, Parser, Token, Variable
from django.template.library import Library
from django.template.loader_tags import IncludeNode, do_include
from django.urls import reverse
from django.utils.safestring import mark_safe

from django_xinclude.cache import ctx_cache
from django_xinclude.conf import conf

if TYPE_CHECKING:
    from collections.abc import KeysView

    from django.contrib.auth.models import AbstractUser, AnonymousUser
    from django.template.base import NodeList
    from django.template.context import RequestContext
    from django.utils.safestring import SafeString

register = Library()


class SpecialVariables:
    _vars = {
        "hx_trigger": "load once",
        "swap_time": None,
        "settle_time": None,
    }

    @classmethod
    def make_context_defaults(cls, ctx: dict[str, Any], parser: Parser) -> None:
        for key, val in cls._vars.items():
            if val is not None:
                ctx.setdefault(key, FilterExpression(f'"{val}"', parser))

    @classmethod
    def keys(cls) -> KeysView[str]:
        return cls._vars.keys()

    @classmethod
    def raw_list(cls) -> list[str]:
        return [k.replace("_", "-") for k in cls._vars.keys()]


class HtmxIncludeNode(IncludeNode):
    def __init__(
        self,
        template: FilterExpression,
        target_template: FilterExpression,
        primary_nodelist: NodeList,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(template, *args, **kwargs)
        self.target_template = target_template
        self.primary_nodelist = primary_nodelist

    def save_context(self, context: RequestContext, fragment_id: str) -> None:
        """
        Save the context data to the cache.
        """
        values = {
            name: var.resolve(context)
            for name, var in self.extra_context.items()
            if name not in SpecialVariables.keys()
        }
        meta: dict[str, Any] = {"template_names": self.get_template_names(context)}
        if user := self.get_user(context):
            meta["user"] = user
        if self.isolated_context:  # using "only"
            ctx = values
        else:
            with context.push(**values):
                ctx = context.flatten()  # type: ignore[assignment]
        ctx = ctx_cache.get_picklable_context(ctx, fragment_id)
        ctx_cache.set(fragment_id, {"meta": meta, "context": ctx})

    def get_user(self, context: RequestContext) -> AbstractUser | AnonymousUser | None:
        try:
            return context.get("user") or context["request"].user  # type: ignore[no-any-return]
        except (KeyError, AttributeError):
            return None

    @property
    def fragment_id(self) -> str:
        return str(uuid.uuid4())

    def sync_include(self, context: RequestContext) -> bool:
        try:
            return getattr(context.request, conf.XINCLUDE_SYNC_REQUEST_ATTR, False)
        except AttributeError:
            return False

    def get_template_names(self, context: RequestContext) -> list[str]:
        tmpt = self.target_template.var
        if isinstance(tmpt, Variable):
            tmpt = tmpt.resolve(context)
            if isinstance(tmpt, str):
                return [tmpt]
            # tmpt should be an Iterable then
            return tmpt  # type: ignore[no-any-return]
        return [tmpt]

    def render(self, context: RequestContext) -> SafeString:  # type: ignore[override]
        if self.sync_include(context):
            self.template = self.target_template
            return super().render(context)
        fragment_id = self.fragment_id
        self.save_context(context, fragment_id)
        context["url"] = (
            f"{reverse('django_xinclude:xinclude')}?fragment_id={fragment_id}"
        )
        if self.primary_nodelist:
            element = self.primary_nodelist.render(context)
            context["primary_nodes"] = mark_safe(element.strip())
        return super().render(context)


@register.tag("xinclude")
def do_xinclude(parser: Parser, token: Token) -> HtmxIncludeNode:
    """
    Render a template using htmx with the current context.
    The context gets passed to the underlying view using the cache framework,.
    Every feature of the regular ``include`` tag is supported.
    You can use the following htmx-specfic arguments:
    - ``hx-trigger``: corresponds to the "hx-trigger" htmx attribute.
        Defaults to "load once".
    - ``swap-time``: corresponds to the "swap" timing of the hx-swap htmx attribute.
    - ``settle-time``:  corresponds to the "settle" timing of the hx-swap
        htmx attribute.

    Example::

        {% xinclude "foo.html" %}{% endxinclude %}
        {% xinclude "foo.html" with foo="bar" only %}{% endxinclude %}

    Use "primary nodes" to render initial content prior to htmx swapping.

        {% xinclude "foo" hx-trigger="intersect once" swap-time="1s" settle-time="1s" %}
            <div>Loading...</div>
        {% endxinclude %}
    """

    bits = token.split_contents()
    remaining_bits = []
    options = {}
    while bits:
        # Find the xinclude-specific arguments and add the rest to remaining_bits
        option = bits.pop(0)
        try:
            key, value = option.split("=", 1)
        except ValueError:
            remaining_bits.append(option)
            continue
        if key in SpecialVariables.raw_list():
            options[key.replace("-", "_")] = FilterExpression(value, parser)
        else:
            remaining_bits.append(option)

    token = Token(
        token.token_type, " ".join(remaining_bits), token.position, token.lineno
    )
    node = do_include(parser, token)  # the regular IncludeNode
    template = FilterExpression('"django_xinclude/include.html"', parser)
    context = {**node.extra_context, **options}
    # add the variable defaults to context
    SpecialVariables.make_context_defaults(context, parser)
    # extract the primary nodes
    primary_nodelist = parser.parse(["endxinclude"])
    parser.delete_first_token()

    return HtmxIncludeNode(
        template,
        target_template=node.template,
        extra_context=context,
        isolated_context=node.isolated_context,
        primary_nodelist=primary_nodelist,
    )
