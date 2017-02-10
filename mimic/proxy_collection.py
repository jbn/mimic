from mimic.util import ProxyProps, setup_logger
from copy import deepcopy


LOGGER = setup_logger('proxy_collection')


class ProxyCollection:
    def __init__(self):
        self._proxies = {}
        self._monitors = {}

    def register_proxy(self, proxy):
        proxy = ProxyProps(**proxy)
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
