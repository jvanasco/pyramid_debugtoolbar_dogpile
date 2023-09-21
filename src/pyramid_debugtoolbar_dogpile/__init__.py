# stdlib
from collections import namedtuple
import logging
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Mapping
from typing import Optional
from typing import Sequence
from typing import TYPE_CHECKING
from typing import Union

# pypi
from dogpile.cache.api import BackendFormatted
from dogpile.cache.api import BackendSetType
from dogpile.cache.api import CacheBackend
from dogpile.cache.api import CachedValue
from dogpile.cache.api import KeyType
from dogpile.cache.api import NO_VALUE
from dogpile.cache.proxy import ProxyBackend
from pyramid.threadlocal import get_current_request

# local
from .panels.pyramid_dogpile import DogpileDebugPanel

if TYPE_CHECKING:
    from pyramid.config import Configurator
    from pyramid.request import Request


__VERSION__ = "0.3.0"


# ==============================================================================


LoggedEvent = namedtuple("LoggedEvent", ["key", "value", "size"])
ApiCall = namedtuple("ApiCall", ["api_call", "duration", "db", "data"])


# ==============================================================================


def includeme(config: "Configurator"):
    logging.debug("includeme")
    config.add_debugtoolbar_panel(DogpileDebugPanel)
    # if 'mako.directories' not in config.registry.settings:
    #    config.registry.settings['mako.directories'] = []


def setup_dogpile_logging(request: "Request") -> Dict:
    """
    calls_raw =  ordered list of calls
    """
    logging.debug("initializing setup_dogpile_logging")
    rval: Dict[str, List] = {"api_calls": []}  # (api_call, duration, db, (k + result))
    return rval


class LoggingProxy(ProxyBackend):
    """
    This is an instance of ProxyBackend
    It times the performance of the backend and logs if we see cache hits or misses
    """

    # None - unset
    # Dict - values
    # False - incompatible backend
    _connection_kwargs: Optional[Union[bool, Dict]] = None
    _db: Optional[Any] = None

    def _derive_db(self):
        """
        this may not have a client on __init__, so this is deferred to
        a @property descriptor
        """
        client: Union[CacheBackend, ProxyBackend] = self
        while hasattr(client, "proxied"):
            # ProxyBackend
            client = client.proxied
        # client is now CacheBackend
        #
        # run this in a try/except block
        # if we fail, or don't have `client`, use the Except block for fallbacks
        try:
            if hasattr(client, "client"):
                # example: redis
                client = client.client
                _connection_kwargs: Dict = (
                    client.connection_pool.connection_kwargs  # type: ignore[union-attr]
                )
                self._connection_kwargs = _connection_kwargs
                self._db = _connection_kwargs["db"]
            else:
                raise ValueError()
        except Exception:
            self._connection_kwargs = False
            self._db = "n/a"

    @property
    def db(self):
        if self._db is None:
            self._derive_db()
        return self._db

    def set(self, key: KeyType, value: BackendSetType) -> None:
        _s = time.time()
        self.proxied.set(key, value)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            r._dogpile_logging["api_calls"].append(
                ApiCall("set", _d, self.db, [LoggedEvent(key, None, None)])
            )

    def set_multi(self, mapping: Mapping[KeyType, BackendSetType]) -> None:
        _s = time.time()
        self.proxied.set_multi(mapping)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            _kvs = [LoggedEvent(k, None, None) for k in mapping.keys()]
            r._dogpile_logging["api_calls"].append(
                ApiCall("set_multi", _d, self.db, _kvs)
            )

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def get(self, key: KeyType) -> BackendFormatted:
        _s = time.time()
        v = self.proxied.get(key)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            r._dogpile_logging["api_calls"].append(
                ApiCall(
                    "get",
                    _d,
                    self.db,
                    [
                        LoggedEvent(
                            key,
                            True if v is not NO_VALUE else False,
                            v.metadata.get("sz", None)
                            if isinstance(v, CachedValue)
                            else None,
                        )
                    ],
                )
            )
        return v

    def get_multi(self, keys: Sequence[KeyType]) -> Sequence[BackendFormatted]:
        _s = time.time()
        vs = self.proxied.get_multi(keys)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            _results = []
            for idx, k in enumerate(keys):
                v = vs[idx]
                _results.append(
                    LoggedEvent(
                        k,
                        True if v is not NO_VALUE else False,
                        v.metadata.get("sz", None)
                        if isinstance(v, CachedValue)
                        else None,
                    )
                )
            r._dogpile_logging["api_calls"].append(
                ApiCall("get_multi", _d, self.db, _results)
            )
        return vs

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def delete(self, key: KeyType) -> None:
        _s = time.time()
        self.proxied.delete(key)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            r._dogpile_logging["api_calls"].append(
                ApiCall("delete", _d, self.db, [LoggedEvent(key, None, None)])
            )

    def delete_multi(self, keys: Sequence[KeyType]) -> None:
        _s = time.time()
        self.proxied.delete_multi(keys)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, "_dogpile_logging"):
            _kvs = [LoggedEvent(k, None, None) for k in keys]
            r._dogpile_logging["api_calls"].append(
                ApiCall("delete_multi", self.db, _d, _kvs)
            )
