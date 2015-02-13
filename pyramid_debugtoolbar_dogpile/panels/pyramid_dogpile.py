# stdlib
import datetime
import logging
import time

# pyramid_debugtoolbar
from pyramid_debugtoolbar.panels import DebugPanel
from pyramid_debugtoolbar.utils import STATIC_PATH
from pyramid_debugtoolbar.utils import ROOT_ROUTE_NAME


# ==============================================================================


class DogpileDebugPanel(DebugPanel):
    """
    """
    name = 'Dogpile'
    template = 'pyramid_debugtoolbar_dogpile.panels:templates/pyramid_dogpile.dbtmako'
    title = 'Dogpile'
    nav_title = 'Dogpile'

    def __init__(self, request):
        self.logs = request.dogpile_logging['api_calls']

    @property
    def has_content(self):
        if self.logs:
            return True
        else:
            return False

    @property
    def nav_subtitle(self):
        if self.logs:
            return "%d" % (len(self.logs))

    def render_content(self, request):
        if not self.logs:
            return 'No logs in request.'

        stats = {}
        for api_call in ('get', 'get_multi', 'set', 'set_multi', 'delete', 'delete_multi', ):
            stats[api_call] = {
                'hit': 0,
                'miss': 0,
                'fractional-hit': 0,
                'fractional-miss': 0,
                'total': 0,
                'total_time': 0,
            }

        for r in self.logs:
            stats[r[0]]['total'] += 1
            stats[r[0]]['total_time'] += r[1]
            # dk - dogpile key
            # dr - dogpile result
            if r[0] == 'get_multi':
                for (dk, dr) in r[2]:
                    if dr is True:
                        stats[r[0]]['fractional-hit'] += 1
                    elif dr is False:
                        stats[r[0]]['fractional-miss'] += 1
            else:
                for (dk, dr) in r[2]:
                    if dr is True:
                        stats[r[0]]['hit'] += 1
                    elif dr is False:
                        stats[r[0]]['miss'] += 1

        self.data = {
            'logs': self.logs,
            'stats': stats,
        }
        return super(DogpileDebugPanel, self).render_content(request)

    def render_vars(self, request):
        return {
            'static_path': request.static_url(STATIC_PATH),
            'root_path': request.route_url(ROOT_ROUTE_NAME)
        }
