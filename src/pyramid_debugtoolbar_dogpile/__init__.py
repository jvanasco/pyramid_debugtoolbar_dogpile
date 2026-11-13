"""Integrate dogpile cache diagnostics with Pyramid Debug Toolbar."""

from collections import namedtuple
import time

from dogpile.cache.api import NO_VALUE, CachedValue
from dogpile.cache.proxy import ProxyBackend
from pyramid.threadlocal import get_current_request

from .panels.pyramid_dogpile import DogpileDebugPanel

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple
    import pyramid.config
    import pyramid.request

__VERSION__ = "0.2.4"

LoggedEvent = namedtuple("LoggedEvent", ["key", "value", "size"])
_timer = getattr(time, "perf_counter", time.time)


def includeme(config):
    # type: (pyramid.config.Configurator) -> None
    """Register the panel and its request-local log."""
    config.add_debugtoolbar_panel(DogpileDebugPanel)
    config.inject_parent_action(_register_request_log)


def _register_request_log(config):
    # type: (pyramid.config.Configurator) -> None
    """Register the request method on the application serving cached views."""
    config.add_request_method(setup_dogpile_logging, "dogpile_logging", reify=True)


def setup_dogpile_logging(request):
    # type: (pyramid.request.Request) -> dict
    """Create the log shared by the proxy and panel for a request."""
    return {"api_calls": []}


def _request_log():
    # type: () -> Optional[List[Tuple[str, float, Any, List[LoggedEvent]]]]
    """Return the operation list when the current request has logging enabled."""
    request = get_current_request()
    logging = getattr(request, "dogpile_logging", None)
    return logging["api_calls"] if logging is not None else None


def _read_event(key, value):
    # type: (Any, Any) -> LoggedEvent
    """Record hit status and a valid size without retaining the cached value."""
    size = value.metadata.get("sz") if isinstance(value, CachedValue) else None
    if not isinstance(size, integer_types) or isinstance(size, bool) or size < 0:
        size = None
    return LoggedEvent(key, value is not NO_VALUE, size)


try:
    integer_types = (int, long)
except NameError:
    integer_types = (int,)


class LoggingProxy(ProxyBackend):
    """Time successful cache operations and log them on the current request."""

    _db = None

    @property
    def db(self):
        # type: () -> Any
        """Read an optional Redis database label without disrupting cache calls."""
        if self._db is None:
            backend = self.proxied
            while isinstance(backend, ProxyBackend):
                backend = backend.proxied
            try:
                self._db = backend.client.connection_pool.connection_kwargs.get(
                    "db", "n/a"
                )
            except Exception:
                # Client discovery is optional and may invoke backend code.
                return "n/a"
        return self._db

    def set(self, key, value):
        # type: (Any, Any) -> None
        """Store one value and record its key."""
        log = _request_log()
        start = _timer()
        self.proxied.set(key, value)
        if log is not None:
            log.append(
                ("set", _timer() - start, self.db, [LoggedEvent(key, None, None)])
            )

    def set_multi(self, mapping):
        # type: (Mapping) -> None
        """Store several values and record their keys."""
        log = _request_log()
        start = _timer()
        self.proxied.set_multi(mapping)
        if log is not None:
            duration = _timer() - start
            events = [LoggedEvent(key, None, None) for key in mapping]
            log.append(("set_multi", duration, self.db, events))

    def get(self, key):
        # type: (Any) -> Any
        """Fetch one value and record its hit status."""
        log = _request_log()
        start = _timer()
        value = self.proxied.get(key)
        if log is not None:
            log.append(("get", _timer() - start, self.db, [_read_event(key, value)]))
        return value

    def get_multi(self, keys):
        # type: (Iterable) -> Sequence
        """Fetch several values and match each result to its key."""
        log = _request_log()
        if log is not None:
            keys = list(keys)
        start = _timer()
        values = self.proxied.get_multi(keys)
        if log is not None:
            duration = _timer() - start
            events = [_read_event(key, value) for key, value in zip(keys, values)]
            log.append(("get_multi", duration, self.db, events))
        return values

    def delete(self, key):
        # type: (Any) -> None
        """Delete one value and record its key."""
        log = _request_log()
        start = _timer()
        self.proxied.delete(key)
        if log is not None:
            log.append(
                ("delete", _timer() - start, self.db, [LoggedEvent(key, None, None)])
            )

    def delete_multi(self, keys):
        # type: (Iterable) -> None
        """Delete several values and record their keys."""
        log = _request_log()
        if log is not None:
            keys = list(keys)
        start = _timer()
        self.proxied.delete_multi(keys)
        if log is not None:
            duration = _timer() - start
            events = [LoggedEvent(key, None, None) for key in keys]
            log.append(("delete_multi", duration, self.db, events))
