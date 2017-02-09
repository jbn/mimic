import logging
import random
from collections import defaultdict
from functools import reduce
from mimic.util import url_from_proxy, ProxyProps


LOGGER = logging.getLogger('mimic.domain_monitor')
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(logging.StreamHandler())


class DomainMonitor:
    """
    The DomainMonitor manages a set of proxies in a target domain context.

    This class does no error management. If you acquire then fail to release
    or delist, it never corrects itself. But, those operations all have
    elements of timing. And, timing is a lower level operation.
    """
    def __init__(self, domain):
        """
        :param domain: the domain being managed, used for logging purposes.
        """
        self._domain = domain
        self._proxies = set()
        self._response_times = {}
        self._acquisitions_processed = 0
        self._props = defaultdict(set)

        LOGGER.info("Initiated DomainMonitor on %s", self._domain)

    @property
    def domain(self):
        return self._domain

    def register(self, proxy_props):
        """
        Add a proxy and index its properties.
        """
        assert isinstance(proxy_props, ProxyProps)  # Refactor shiv

        proxy = str(proxy_props)

        if proxy in self._proxies:
            LOGGER.info("%s already registered with DomainMonitor(%s)", proxy,
                        self._domain)
        else:
            self._proxies.add(proxy)
            self._response_times[proxy] = proxy_props.resp_time

            for k in ['geo', 'anon_level']:
                v = getattr(proxy_props, k)
                if v is not None:
                    self._props[v].add(proxy)

            LOGGER.info("Registered %s with DomainMonitor(%s)", proxy,
                        self._domain)

    def delist(self, proxy):
        """
        Remove a proxy and remove its properties from all indices.
        """
        assert isinstance(proxy, str)

        self._proxies.remove(proxy)
        del self._response_times[proxy]

        keys_to_delete = []
        for prop, proxy_set in self._props.items():
            if proxy in proxy_set:
                proxy_set.remove(proxy)
            if not proxy_set:
                keys_to_delete.append(prop)

        for k in keys_to_delete:
            del self._props[k]

        LOGGER.info("Delisted %s with DomainMonitor(%s)", proxy, self._domain)

    def acquire(self, *requirements):
        """
        Acquire a proxy for use.

        :param requirements: optional tags to match
        """
        # This is a conjunction. What about an disjunction (e.g. country code)
        def _query(proxies, prop):
            return {p for p in proxies if p in self._props[prop]}

        LOGGER.info("Acquiring proxy from DomainMonitor(%s) over reqs=%s",
                    self._domain, requirements)

        candidates = list(reduce(_query, requirements, self._proxies))
        if len(candidates) == 0:
            return None  # None available right now.

        proxy = self._sample_proxy(candidates)
        self._proxies.remove(proxy)

        self._acquisitions_processed += 1

        return proxy

    def release(self, proxy, response_time):
        """
        Return this proxy so other requestors can use it.
        """
        assert proxy is not None, "Attempting to release None!"  # BUGTEST

        if proxy in self._proxies:
            # This means that the auto-return already returned it.
            # TODO: Should be auto-reacquired, for wait seconds for correct
            # throttling.
            LOGGER.info("%s already on DomainMonitor(%s)", proxy, self._domain)

            # Hrm. I think this needs a special flag for released by
            # auto-return or client...

            if response_time > 0:
                self._response_times[proxy] = response_time
        else:
            self._proxies.add(proxy)
            if response_time > 0:
                self._response_times[proxy] = response_time

            LOGGER.info("%s ready again on DomainMonitor(%s)",
                        proxy, self._domain)

    def average_response_time(self):
        """
        The average of the last request's response time over each proxy.
        """
        n = len(self._response_times)

        if n == 0:  # You'll wait forever, since there are no proxies.
            return float("inf")

        return sum(self._response_times.values()) / n

    def stats(self):
        return {'available': len(self._proxies),
                'acquisitions_processed': self._acquisitions_processed,
                'avg_resp_time': self.average_response_time(),
                'indices': {k: len(v) for k, v in self._props.items()}}

    def _sample_proxy(self, proxies, min_offset=0.01):
        # Network conditions change. Selection is a function of the average
        # response time. It's stochastic to avoid synchronization issues but
        # weighted in favor of faster proxies.
        #
        # Do stochastic acceptance for fast proportional selection.
        # See: http://jbn.github.io/fast_proportional_selection/
        min_resp_time, max_resp_time, resp_times = 1000000000, -1, []
        for proxy in proxies:
            resp_time = self._response_times[proxy]
            if resp_time > max_resp_time:
                max_resp_time = resp_time
            if resp_time < min_resp_time:
                min_resp_time = resp_time
            resp_times.append(resp_time)

        if max_resp_time == 0.0:
            return random.choice(proxies)

        n = len(proxies)
        while True:
            i = int(n * random.random())
            score = max_resp_time - (resp_times[i] - min_resp_time)
            if random.random() < score:
                return proxies[i]
