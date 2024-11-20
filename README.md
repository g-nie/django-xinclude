# django-xinclude

[![PyPI version](https://img.shields.io/pypi/v/django-xinclude.svg)](https://pypi.org/project/django-xinclude/)

Render a template using htmx with the current context.

> [!IMPORTANT]
> This package currently contains minimal features and is a work-in-progress.

------------------------------------------------------------------------

`hx-get` is often used to delegate potentially computationally expensive
template fragments to `htmx`.  
Achieving this sometimes requires more views, each of which needs to inherit
from mixins that provide access to the same context.  
`django-xinclude` provides a template tag that aims to make this easier by leveraging the cache.

## Requirements

-   Python 3.10 to 3.12 supported.
-   Django 4.2 to 5.0 supported.
-   [htmx](https://htmx.org/)

## Setup

-   Install from **pip**:

``` sh
python -m pip install django-xinclude
```

-   Add it to your installed apps:

``` python
INSTALLED_APPS = [
    ...,
    "django_xinclude",
    ...,
]
```

-   Include the app URLs in your root URLconf:

``` python
from django.urls import include, path

urlpatterns = [
    ...,
    path("__xinclude__/", include("django_xinclude.urls")),
]
```

You can use a different prefix if required.

## Usage

Once installed, load the `xinclude` library and use the tag passing the
template that you want to include:

``` html
{% load xinclude %}

{% xinclude "footer.html" %}{% endxinclude %}
```

Every feature of the regular [`include`](https://docs.djangoproject.com/en/dev/ref/templates/builtins/#include) tag is supported, including
the use of `with` and `only`.

You can use the following htmx-specific arguments:

-   `hx-trigger`: corresponds to the [`hx-trigger`](https://htmx.org/attributes/hx-trigger/) htmx attribute.
    Defaults to `load once`.
-   `swap-time`: corresponds to the `swap` timing of the [`hx-swap`](https://htmx.org/attributes/hx-swap/#timing-swap-settle)
    htmx attribute.
-   `settle-time`: corresponds to the `settle` timing of the
    [`hx-swap`](https://htmx.org/attributes/hx-swap/#timing-swap-settle) htmx attribute.

"Primary nodes" may be passed along to render initial content prior to
htmx swapping. For example:

``` html
{% xinclude "footer.html" %}
    <div>Loading...</div>
{% endxinclude %}
```

`django-xinclude` plays well with the excellent
[django-template-partials](https://github.com/carltongibson/django-template-partials/)
package, to select specific partials on the target template.

### Advanced usage

Below is a more complete example making use of the htmx [transition
classes](https://htmx.org/examples/animations/#swapping). Note the
`intersect once` trigger, which will fire the request once when the
element intersects the viewport.

``` html
<style>
.htmx-swapping > #loading {
    opacity: 0;
    transition: opacity 1s ease-out;
}
</style>

{% xinclude "magic.html" with wand="🪄" hx-trigger="intersect once" swap-time="1s" settle-time="1s" %}
    <div id="loading">
        Loading...
    </div>
{% endxinclude %}
```

`magic.html`:

``` html
<style>
#items.htmx-added {
    opacity: 1;
    animation: appear ease-in 500ms;
}
</style>

<div id="items">
    🔮 {{ wand }}
</div>
```

------------------------------------------------------------------------

You can preload the `xinclude` libary in every template by appending to
your `TEMPLATES` `builtins` setting. This way you don't need to repeat
the `{% load xinclude %}` in every template that you need the tag:

``` python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # ...,
        "OPTIONS": {
            "builtins": [
                "django_xinclude.templatetags.xinclude",
            ],
        },
    },
]
```

## How It Works

`django-xinclude` first checks if it needs to render the target template
synchronously; see the [Section below](#rendering-synchronously) for
cases where this might be useful. If this is not the case, it stores the
current context and the target template to the cache and constructs a
url with a `fragment_id` that targets an internal view. It then renders
a parent `div` element containing all the necessary htmx attributes.
Once the htmx request fires, the view fetches the cache context and
template that match the passed `fragment_id` and uses that context to
render the template.

### Cache

`django-xinclude` uses either the cache that corresponds to the
`XINCLUDE_CACHE_ALIAS` setting, if specified, or `CACHES["default"]`.
When setting a new cache key, it finds unpicklable values and discards
them. If you want to see which keys get discarded, update your
`settings.LOGGERS` to include `"django_xinclude"` with
`"level": "DEBUG"`.

All official [Django cache backends](https://docs.djangoproject.com/en/5.0/ref/settings/#backend) should work, under one **important condition**:  
Your cache should be accessible from all your app instances. If you are using
multi-processing for your Django application, or multiple servers clusters,
make sure that your `django-xinclude` cache is accessible from all the instances,
otherwise your requests will result in 404s.

### Authorization

The request user is expected to be the one that initially accessed the
original view (and added to cache), or `AnonymousUser` in both cases;
otherwise `django-xinclude` will return 404 for the htmx requests. If
`request.user` is not available, for instance when `django.contrib.auth`
is not in the `INSTALLED_APPS`, then `django-xinclude` assumes that the
end user can access the data.

### Rendering synchronously

There are cases where you might want to conditionally render fragments
synchronously (i.e. use the regular `include`). For example, you could
render synchronously for SEO purposes, when robots are crawling your
pages, but still make use of the htmx functionality for regular users.
`django-xinclude` supports this, it checks for a `xinclude_sync`
attribute on the request and renders synchronously if that evaluates to
`True`. So you can add a custom middleware that sets the `xinclude_sync`
attribute upon your individual conditions.

See also [Configuration](#configuration) below for the
`XINCLUDE_SYNC_REQUEST_ATTR` setting.

## Configuration

### `XINCLUDE_CACHE_ALIAS: str`

The cache alias that `django-xinclude` will use, it defaults to
`CACHES["default"]`.

### `XINCLUDE_CACHE_TIMEOUT: int`

The number of seconds that contexts will remain in cache. If the setting
is not present, Django will use the default timeout argument of the
appropriate backend in the `CACHES` setting.

### `XINCLUDE_SYNC_REQUEST_ATTR: str`

The request attribute that `django-xinclude` will check on to determine
if it needs to render synchronously. It defaults to `xinclude_sync`.

## Running the tests

Fork, then clone the repo:

``` sh
git clone git@github.com:your-username/django-xinclude.git
```

Set up a venv:

``` sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[tests,dev]'
```

Set up the [`pre-commit`](https://pre-commit.com/) hooks:

``` sh
pre-commit install
```

Then you can run the tests with the [`just`](https://github.com/casey/just) command runner:

``` sh
just test
```

Or with coverage:

``` sh
just coverage
```

If you don't have `just` installed, you can look in the `justfile` for
the commands that are run.

## Complementary packages

-   [`django-htmx`](https://github.com/adamchainz/django-htmx) : Extensions for using Django with htmx.
-   [`django-template-partials`](https://github.com/carltongibson/django-template-partials/): Reusable named inline partials for
    the Django Template Language.
