# stdlib
from typing import Dict
from typing import List
from typing import Optional
from typing import TYPE_CHECKING

# pyramid_debugtoolbar
from pyramid_debugtoolbar.panels import DebugPanel
from pyramid_debugtoolbar.utils import ROOT_ROUTE_NAME
from pyramid_debugtoolbar.utils import STATIC_PATH

if TYPE_CHECKING:
    from pyramid.request import Request

# ==============================================================================


dogpile_api_calls = (
    "get",
    "get_multi",
    "set",
    "set_multi",
    "delete",
    "delete_multi",
)


class DogpileDebugPanel(DebugPanel):
    """"""

    name = "Dogpile"
    template = "pyramid_debugtoolbar_dogpile.panels:templates/pyramid_dogpile.dbtmako"
    title = "Dogpile"
    nav_title = "Dogpile"
    logs: Optional[List]

    def __init__(self, request: "Request"):
        # set this attribute
        _dogpile_logging: Dict = {"api_calls": []}
        request._dogpile_logging = _dogpile_logging
        self.logs = _dogpile_logging["api_calls"]

    @property
    def has_content(self) -> bool:
        if self.logs:
            return True
        else:
            return False

    @property
    def nav_subtitle(self) -> Optional[str]:
        if self.logs:
            return "%d" % (len(self.logs))
        return None

    def render_content(self, request: "Request") -> str:
        if not self.logs:
            return "No logs in request."
        stats: Dict[str, Dict[str, int]] = {}
        for api_call in dogpile_api_calls:
            stats[api_call] = {
                "hit": 0,
                "miss": 0,
                "fractional-hit": 0,
                "fractional-miss": 0,
                "total": 0,
                "total_time": 0,
                "size": 0,
            }
        for r in self.logs:
            stats[r[0]]["total"] += 1
            stats[r[0]]["total_time"] += r[1]
            # dk - dogpile key
            # dr - dogpile result
            if r[0] == "get_multi":
                for dk, dr, dsize in r[3]:
                    if dr is True:
                        stats[r[0]]["fractional-hit"] += 1
                    elif dr is False:
                        stats[r[0]]["fractional-miss"] += 1
                    if dsize is not None:
                        stats[r[0]]["size"] += dsize
            else:
                for dk, dr, dsize in r[3]:
                    if dr is True:
                        stats[r[0]]["hit"] += 1
                    elif dr is False:
                        stats[r[0]]["miss"] += 1
                    if dsize is not None:
                        stats[r[0]]["size"] += dsize
        total_size = 0
        for api_call in dogpile_api_calls:
            total_size += stats[api_call]["size"]
        self.data = {"logs": self.logs, "stats": stats, "has_size": bool(total_size)}
        return super(DogpileDebugPanel, self).render_content(request)

    def render_vars(self, request: "Request") -> Dict:
        r: Dict = {
            "static_path": request.static_url(STATIC_PATH),
            "root_path": request.route_url(ROOT_ROUTE_NAME),
        }
        return r
