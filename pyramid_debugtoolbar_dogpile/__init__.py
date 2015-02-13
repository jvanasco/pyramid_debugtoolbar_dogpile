# stdlib
import logging
import time

# pyramid
from pyramid.threadlocal import get_current_request

# dogpile
import dogpile
from dogpile.cache.api import NO_VALUE, CachedValue
from dogpile.cache.proxy import ProxyBackend


# local
from .panels.pyramid_dogpile import DogpileDebugPanel


def includeme(config):
    config.registry.settings['debugtoolbar.panels'].append(DogpileDebugPanel)
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
    print "initializing setup_dogpile_logging"
    return {
        'api_calls': [],  # (api_call, duration, (k + result))
    }


class LoggingProxy(ProxyBackend):
    """
    This is an instance of ProxyBackend
    It times the performance of the backend and logs if we see cache hits or misses
    """

    def set(self, key, value):
        _s = time.time()
        self.proxied.set(key, value)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r:
            r.dogpile_logging['api_calls'].append(("set", _d, [(key, None), ]))

    def set_multi(self, mapping):
        _s = time.time()
        self.proxied.set_multi(mapping)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r:
            _kvs = [(k, None) for k in mapping.keys()]
            r.dogpile_logging['api_calls'].append(("set_multi", _d, _kvs))

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def get(self, key):
        _s = time.time()
        v = self.proxied.get(key)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r:
            r.dogpile_logging['api_calls'].append(("get", _d, [(key, True if v is not NO_VALUE else False), ]))
        return v

    def get_multi(self, keys):
        _s = time.time()
        vs = self.proxied.get_multi(keys)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r:
            _results = [(True if v is not NO_VALUE else False) for v in vs]
            _dictionary = dict(zip(keys, _results))
            r.dogpile_logging['api_calls'].append(("get_multi", _d, _dictionary.items()))
        return vs

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    def delete(self, key):
        _s = time.time()
        self.proxied.delete(key)
        _f = time.time()
        _d = _f - _s
        r = get_current_request()
        if r:
            r.dogpile_logging['api_calls'].append(("delete", _d, [(key, None), ]))

    def delete_multi(self, keys):
        _s = time.time()
        self.proxied.delete_multi(keys)
        _f = time.time()
        _d = _f - _s

        r = get_current_request()
        if r:
            _kvs = [(k, None) for k in keys]
            r.dogpile_logging['api_calls'].append(("delete_multi", _d, _kvs))
