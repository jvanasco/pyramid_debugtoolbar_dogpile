# stdlib
import re
import unittest

# pyramid testing requirements
from dogpile.cache import make_region
from pyramid import testing
from pyramid.request import Request
from pyramid.response import Response

# from pyramid.exceptions import ConfigurationError

from pyramid_debugtoolbar_dogpile import LoggingProxy as DogpileLoggingProxy

# ------------------------------------------------------------------------------


# used to ensure the toolbar link is injected into requests
re_toolbar_link = re.compile(r'(?:href="http://localhost)(/_debug_toolbar/[\d]+)"')


class TestProxy(unittest.TestCase):
    def setUp(self):
        self.CACHE_DICTIONARY = {}
        self.CACHE_REGION = make_region().configure(
            "dogpile.cache.memory",
            arguments={"cache_dict": self.CACHE_DICTIONARY},
            wrap=[
                DogpileLoggingProxy,
            ],
        )

        self.config = config = testing.setUp()
        config.add_settings({"debugtoolbar.includes": ["pyramid_debugtoolbar_dogpile"]})
        config.include("pyramid_debugtoolbar")
        self.settings = config.registry.settings

        # create a view
        def active_view(request):
            # set something
            r_set = self.CACHE_REGION.set("foo", "bar")
            # get something
            r_get = self.CACHE_REGION.get("foo")
            self.assertEqual(r_get, "bar")
            # ensure it hits the backend
            self.assertIn("foo", self.CACHE_DICTIONARY)
            return Response(
                "<html><head></head><body>ActiveView</body></html>",
                content_type="text/html",
            )

        config.add_route("active_route", "/active")
        config.add_view(active_view, route_name="active_route")

    def tearDown(self):
        testing.tearDown()

    def test_panel_works(self):
        # make the app
        app = self.config.make_wsgi_app()
        # make a request
        req1 = Request.blank("/active")
        req1.remote_addr = "127.0.0.1"
        resp1 = req1.get_response(app)
        self.assertEqual(resp1.status_code, 200)
        self.assertIn("ActiveView", resp1.text)
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
        self.assertNotIn('<li class="disabled" id="pDebugPanel-Dogpile">', resp2.text)
        self.assertIn(
            '<div id="pDebugPanel-Dogpile-content" class="panelContent" style="display: none;">',
            resp2.text,
        )
        self.assertIn(
            """<div class="pDebugPanelTitle">
              <h3>Dogpile</h3>
            </div>""",
            resp2.text,
        )
