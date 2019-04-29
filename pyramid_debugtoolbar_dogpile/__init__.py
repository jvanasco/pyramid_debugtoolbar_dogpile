from __future__ import print_function
# stdlib
from collections import namedtuple
import logging
import time

# pyramid
from pyramid.threadlocal import get_current_request

# dogpile
from dogpile.cache.api import NO_VALUE, CachedValue
from dogpile.cache.proxy import ProxyBackend

# local
from .panels.pyramid_dogpile import DogpileDebugPanel


__VERSION__ = '0.2.1'

# ==============================================================================


LoggedEvent = namedtuple('LoggedEvent', ['key', 'value', 'size', ])


# ==============================================================================


def includeme(config):
    config.registry.settings['debugtoolbar.extra_panels'].append(DogpileDebugPanel)
    if 'mako.directories' not in config.registry.settings:
        config.registry.settings['mako.directories'] = []

    # custom property || app_domain / DomainObject
    config.add_request_method(
        'pyramid_debugtoolbar_dogpile.setup_dogpile_logging',
        'dogpile_logging',
        reify=True,
    )


def setup_dogpile_logging(request):
    """
        calls_raw =  ordered list of calls
    """
    logging.debug('initializing setup_dogpile_logging')
    return {'api_calls': [],  # (api_call, duration, db, (k + result))
            }


class LoggingProxy(ProxyBackend):
    """
    This is an instance of ProxyBackend
    It times the performance of the backend and logs if we see cache hits or misses
    """
    _connection_kwargs = None
    _db = None

    def _derive_db(self):
        """
        this may not have a client on __init__, so this is deferred to
        a @property descriptor
        """
        client = self
        while hasattr(client, 'proxied'):
            client = client.proxied
        if hasattr(client, 'client'):
            client = client.client
            self._connection_kwargs = client.connection_pool.connection_kwargs
            self._db = self._connection_kwargs['db']
        else:
            self._connection_kwargs = False
            self._db = 'n/a'

    @property
    def db(self):
        if self._db is None:
            self._derive_db()
        return self._db

    def set(self, key, value):
        _s = time.time()
        self.proxied.set(key, value)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            r.dogpile_logging['api_calls'].append(("set", _d, self.db, [LoggedEvent(key, None, None), ]))

    def set_multi(self, mapping):
        _s = time.time()
        self.proxied.set_multi(mapping)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            _kvs = [LoggedEvent(k, None, None)
                    for k in mapping.keys()
                    ]
            r.dogpile_logging['api_calls'].append(("set_multi", _d, self.db, _kvs))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def get(self, key):
        _s = time.time()
        v = self.proxied.get(key)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            r.dogpile_logging['api_calls'].append(("get", _d, self.db, [LoggedEvent(key,
                                                                                    True if v is not NO_VALUE else False,
                                                                                    v.metadata.get('sz', None) if isinstance(v, CachedValue) else None,
                                                                                    ),
                                                                        ]))
        return v

    def get_multi(self, keys):
        _s = time.time()
        vs = self.proxied.get_multi(keys)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            _results = []
            for (idx, k) in enumerate(keys):
                v = vs[idx]
                _results.append(LoggedEvent(k,
                                            True if v is not NO_VALUE else False,
                                            v.metadata.get('sz', None) if isinstance(v, CachedValue) else None,
                                            )
                                )
            r.dogpile_logging['api_calls'].append(("get_multi", _d, self.db, _results))
        return vs

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def delete(self, key):
        _s = time.time()
        self.proxied.delete(key)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            r.dogpile_logging['api_calls'].append(("delete", _d, self.db, [LoggedEvent(key, None, None), ]))

    def delete_multi(self, keys):
        _s = time.time()
        self.proxied.delete_multi(keys)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r and hasattr(r, 'dogpile_logging'):
            _kvs = [LoggedEvent(k, None, None)
                    for k in keys
                    ]
            r.dogpile_logging['api_calls'].append(("delete_multi", self.db, _d, _kvs))
