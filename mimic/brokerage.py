from mimic.broker import Broker
from mimic.domain_monitor import DomainMonitor
from mimic.util import parse_and_intern_domain


class Brokerage:
    def __init__(self, proxy_collection, broker_opts=None):
        self._proxy_collection = proxy_collection
        self._broker_opts = broker_opts or {}
        self._brokers = {}

    async def acquire(self, request_url, requirements, max_wait_time):
        domain = parse_and_intern_domain(request_url)
        broker = self._brokers.get(domain)
        if not broker:
            monitor = DomainMonitor(domain)
            self._proxy_collection.register_domain_monitor(monitor)
            broker = Broker(monitor, **self._broker_opts)
            self._brokers[domain] = broker

        return {'broker': domain,
                'proxy': await broker.acquire(*requirements,
                                              max_wait_time=max_wait_time)}

    async def release(self, domain, proxy, response_time, is_failure):
        broker = self._brokers.get(domain)
        if not broker:
            return False

        broker.release(proxy, response_time, is_failure)
        return True

    def list_all(self):
        return {k: v.stats() for k, v in self._brokers.items()}

    def delete(self, broker):
        pass

    def register_on_all(self, proxy_obj):
        for broker in self._brokers.values():
            broker.monitor.register(proxy_obj)
