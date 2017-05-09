# stdlib

# pyramid_debugtoolbar
from pyramid_debugtoolbar.panels import DebugPanel
from pyramid_debugtoolbar.utils import STATIC_PATH
from pyramid_debugtoolbar.utils import ROOT_ROUTE_NAME


# ==============================================================================


dogpile_api_calls = ('get',
                     'get_multi',
                     'set',
                     'set_multi',
                     'delete',
                     'delete_multi',
                     )


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
        for api_call in dogpile_api_calls:
            stats[api_call] = {'hit': 0,
                               'miss': 0,
                               'fractional-hit': 0,
                               'fractional-miss': 0,
                               'total': 0,
                               'total_time': 0,
                               'size': 0,
                               }
        for r in self.logs:
            stats[r[0]]['total'] += 1
            stats[r[0]]['total_time'] += r[1]
            # dk - dogpile key
            # dr - dogpile result
            if r[0] == 'get_multi':
                for (dk, dr, dsize) in r[3]:
                    if dr is True:
                        stats[r[0]]['fractional-hit'] += 1
                    elif dr is False:
                        stats[r[0]]['fractional-miss'] += 1
                    if dsize is not None:
                        stats[r[0]]['size'] += dsize
            else:
                for (dk, dr, dsize) in r[3]:
                    if dr is True:
                        stats[r[0]]['hit'] += 1
                    elif dr is False:
                        stats[r[0]]['miss'] += 1
                    if dsize is not None:
                        stats[r[0]]['size'] += dsize
        total_size = 0
        for api_call in dogpile_api_calls:
            total_size += stats[api_call]['size']
        self.data = {'logs': self.logs,
                     'stats': stats,
                     'has_size': bool(total_size),
                     }
        return super(DogpileDebugPanel, self).render_content(request)

    def render_vars(self, request):
        return {'static_path': request.static_url(STATIC_PATH),
                'root_path': request.route_url(ROOT_ROUTE_NAME)
                }
