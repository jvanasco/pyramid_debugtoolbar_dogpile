# stdlib
import re
import unittest

from dogpile.cache import make_region
from dogpile.cache.api import CachedValue, NO_VALUE
from dogpile.cache.proxy import ProxyBackend
import pytest

from pyramid_debugtoolbar_dogpile import LoggingProxy

# pyramid testing requirements
from pyramid import testing
from pyramid.response import Response
from pyramid.request import Request

# ------------------------------------------------------------------------------


# used to ensure the toolbar link is injected into requests
re_toolbar_link = re.compile(r'(?:href="http://localhost)(/_debug_toolbar/[\d]+)"')


class TestDebugtoolbarPanel(unittest.TestCase):
    def setUp(self):
        self.config = config = testing.setUp()
        config.add_settings({"debugtoolbar.includes": ["pyramid_debugtoolbar_dogpile"]})
        config.include("pyramid_debugtoolbar")
        self.settings = config.registry.settings

        # create a view
        def empty_view(request):
            return Response(
                "<html><head></head><body>OK</body></html>", content_type="text/html"
            )

        config.add_view(empty_view)

    def tearDown(self):
        testing.tearDown()

    def test_panel_injected(self):

        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("http://localhost/_debug_toolbar/", resp1.text)

        # check the toolbar
        links = re_toolbar_link.findall(resp1.text)
        self.assertIsNotNone(links)
        self.assertIsInstance(links, list)
        self.assertEqual(len(links), 1)
        toolbar_link = links[0]

        req2 = Request.blank(toolbar_link)
        req2.remote_addr = "127.0.0.1"
        resp2 = req2.get_response(app)
        self.assertEqual(resp2.status_code, 200)

        # we haven't logged anything, so:
        # * `class="disabled"`
        # * no content panel rendered
        self.assertIn('<li class="disabled" id="pDebugPanel-Dogpile">', resp2.text)
        self.assertNotIn(
            '<div id="pDebugPanel-Dogpile-content" class="panelContent" style="display: none;">',
            resp2.text,
        )
        self.assertNotIn(
            """<div class="pDebugPanelTitle">
              <h3>Dogpile</h3>
            </div>""",
            resp2.text,
        )

    def test_populated_panel(self):
        # type: () -> None
        """Show logged cache calls and escape backend-supplied text."""
        key = "<em>cache-key</em>"
        database = "<em>database</em>"
        region = make_region().configure("dogpile.cache.memory", wrap=[LoggingProxy])
        backend = region.backend
        backend._db = database

        def cache_view(request):
            # type: (Request) -> Response
            region.set(key, "cached")
            values = backend.get_multi(iter([key, "missing"]))
            assert isinstance(values[0], CachedValue)
            assert values[1] is NO_VALUE
            backend.delete_multi(iter([key]))
            assert len(request.dogpile_logging["api_calls"]) == 3
            return Response("<html><body>OK</body></html>", content_type="text/html")

        self.config.add_settings({"debugtoolbar.intercept_exc": False})
        self.config.add_route("cache", "/cache")
        self.config.add_view(cache_view, route_name="cache")
        app = self.config.make_wsgi_app()
        request = Request.blank("/cache", remote_addr="127.0.0.1")
        response = request.get_response(app)
        self.assertEqual(response.status_code, 200)
        (link,) = re_toolbar_link.findall(response.text)
        toolbar = Request.blank(link, remote_addr="127.0.0.1").get_response(app)
        self.assertEqual(toolbar.status_code, 200)
        self.assertIn("delete_multi", toolbar.text)
        self.assertIn("&lt;em&gt;cache-key&lt;/em&gt;", toolbar.text)
        self.assertIn("&lt;em&gt;database&lt;/em&gt;", toolbar.text)
        self.assertNotIn(key, toolbar.text)
        self.assertNotIn(database, toolbar.text)


def test_optional_metadata():
    # type: () -> None
    """Keep cache operations usable when diagnostic metadata is unavailable."""
    request = testing.DummyRequest(dogpile_logging={"api_calls": []})
    testing.setUp(request=request)
    try:
        region = make_region().configure("dogpile.cache.memory", wrap=[LoggingProxy])
        backend = region.backend

        class UnavailableClient(object):
            @property
            def connection_pool(self):
                # type: () -> None
                raise RuntimeError("no Redis connection pool")

        backend.proxied.client = UnavailableClient()
        value = CachedValue("cached", {"sz": "invalid"})
        backend.set("key", value)
        assert backend.get("key") is value
        _, duration, database, events = request.dogpile_logging["api_calls"][-1]
        assert duration >= 0
        assert database == "n/a"
        assert events == [("key", True, None)]
    finally:
        testing.tearDown()


def test_without_request():
    # type: () -> None
    """Allow cache operations without a Pyramid request."""
    region = make_region().configure("dogpile.cache.memory", wrap=[LoggingProxy])
    region.set("key", "cached")
    assert region.get("key") == "cached"
    region.delete("key")
    assert region.get("key") is NO_VALUE


@pytest.mark.skipif(
    not hasattr(ProxyBackend, "get_serialized"),
    reason="installed dogpile.cache has no serialized backend API",
)
def test_serialized_operations():
    # type: () -> None
    """Log serialized backend operations without retaining payload bytes."""
    request = testing.DummyRequest(dogpile_logging={"api_calls": []})
    testing.setUp(request=request)
    try:
        region = make_region().configure(
            "dogpile.cache.memory_pickle", wrap=[LoggingProxy]
        )
        region.set("one", "first")
        region.set_multi({"two": "second"})
        assert region.get("one") == "first"
        assert region.get_multi(["two", "missing"]) == ["second", NO_VALUE]
        logs = request.dogpile_logging["api_calls"]
        assert [(name, events) for name, _, _, events in logs] == [
            ("set", [("one", None, None)]),
            ("set_multi", [("two", None, None)]),
            ("get", [("one", True, None)]),
            ("get_multi", [("two", True, None), ("missing", False, None)]),
        ]
    finally:
        testing.tearDown()
