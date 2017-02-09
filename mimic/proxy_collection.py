import logging
from mimic.util import url_from_proxy, ProxyProps
from copy import deepcopy


LOGGER = logging.getLogger('mimic.proxy_collection')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


class ProxyCollection:
    def __init__(self):
        self._proxies = {}
        self._monitors = {}

    def register_proxy(self, proxy):
        proxy = ProxyProps(**proxy)
        #url = url_from_proxy(proxy)
        self._proxies[str(proxy)] = proxy
        for monitor in self._monitors.values():
            monitor.register(proxy)
        LOGGER.info("ProxyCollection registering %s", str(proxy))

    def register_domain_monitor(self, monitor):
        self._monitors[monitor.domain] = monitor
        for proxy in self._proxies.values():
            monitor.register(proxy)

    @property
    def proxies(self):
        return deepcopy(self._proxies)
