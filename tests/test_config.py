from __future__ import print_function
from __future__ import unicode_literals

# stdlib
import re
import unittest

# pyramid testing requirements
from pyramid import testing
from pyramid.exceptions import ConfigurationError
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
