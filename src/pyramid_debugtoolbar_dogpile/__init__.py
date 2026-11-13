"""Integrate dogpile cache diagnostics with Pyramid Debug Toolbar."""

from collections import namedtuple
from time import perf_counter

from dogpile.cache.api import NO_VALUE, CachedValue
from dogpile.cache.proxy import ProxyBackend
from pyramid.threadlocal import get_current_request

from .panels.pyramid_dogpile import DogpileDebugPanel

try:
    from typing import TYPE_CHECKING
except ImportError:  # Python 3.5.0 and 3.5.1 lack TYPE_CHECKING.
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Any, Callable, Iterable, List, Mapping, Optional, Sequence, Tuple
    import pyramid.config
    import pyramid.request

__VERSION__ = "0.2.4"

LoggedEvent = namedtuple("LoggedEvent", ["key", "value", "size"])


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
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        size = None
    return LoggedEvent(key, value is not NO_VALUE, size)


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
        return self._log_set(self.proxied.set, key, value)

    def set_serialized(self, key, value):
        # type: (Any, bytes) -> None
        """Record a serialized backend call under its ordinary operation name."""
        return self._log_set(self.proxied.set_serialized, key, value)

    def _log_set(self, operation, key, value):
        # type: (Callable[[Any, Any], None], Any, Any) -> None
        """Time the backend call and record the result in the request log."""
        log = _request_log()
        start = perf_counter()
        operation(key, value)
        if log is not None:
            log.append(
                ("set", perf_counter() - start, self.db, [LoggedEvent(key, None, None)])
            )

    def set_multi(self, mapping):
        # type: (Mapping) -> None
        """Store several values and record their keys."""
        return self._log_set_multi(self.proxied.set_multi, mapping)

    def set_serialized_multi(self, mapping):
        # type: (Mapping[Any, bytes]) -> None
        """Record a serialized backend call under its ordinary operation name."""
        return self._log_set_multi(self.proxied.set_serialized_multi, mapping)

    def _log_set_multi(self, operation, mapping):
        # type: (Callable[[Mapping], None], Mapping) -> None
        """Time the backend call and record the result in the request log."""
        log = _request_log()
        start = perf_counter()
        operation(mapping)
        if log is not None:
            duration = perf_counter() - start
            events = [LoggedEvent(key, None, None) for key in mapping]
            log.append(("set_multi", duration, self.db, events))

    def get(self, key):
        # type: (Any) -> Any
        """Fetch one value and record its hit status."""
        return self._log_get(self.proxied.get, key)

    def get_serialized(self, key):
        # type: (Any) -> Any
        """Record a serialized backend call under its ordinary operation name."""
        return self._log_get(self.proxied.get_serialized, key)

    def _log_get(self, operation, key):
        # type: (Callable[[Any], Any], Any) -> Any
        """Time the backend call and record the result in the request log."""
        log = _request_log()
        start = perf_counter()
        value = operation(key)
        if log is not None:
            log.append(
                ("get", perf_counter() - start, self.db, [_read_event(key, value)])
            )
        return value

    def get_multi(self, keys):
        # type: (Iterable) -> Sequence
        """Fetch several values and match each result to its key."""
        return self._log_get_multi(self.proxied.get_multi, keys)

    def get_serialized_multi(self, keys):
        # type: (Iterable) -> Sequence
        """Record a serialized backend call under its ordinary operation name."""
        return self._log_get_multi(self.proxied.get_serialized_multi, keys)

    def _log_get_multi(self, operation, keys):
        # type: (Callable[[Iterable], Sequence], Iterable) -> Sequence
        """Time the backend call and record the result in the request log."""
        log = _request_log()
        if log is not None:
            keys = list(keys)
        start = perf_counter()
        values = operation(keys)
        if log is not None:
            duration = perf_counter() - start
            events = [_read_event(key, value) for key, value in zip(keys, values)]
            log.append(("get_multi", duration, self.db, events))
        return values

    def delete(self, key):
        # type: (Any) -> None
        """Delete one value and record its key."""
        log = _request_log()
        start = perf_counter()
        self.proxied.delete(key)
        if log is not None:
            log.append(
                (
                    "delete",
                    perf_counter() - start,
                    self.db,
                    [LoggedEvent(key, None, None)],
                )
            )

    def delete_multi(self, keys):
        # type: (Iterable) -> None
        """Delete several values and record their keys."""
        log = _request_log()
        if log is not None:
            keys = list(keys)
        start = perf_counter()
        self.proxied.delete_multi(keys)
        if log is not None:
            duration = perf_counter() - start
            events = [LoggedEvent(key, None, None) for key in keys]
            log.append(("delete_multi", duration, self.db, events))
