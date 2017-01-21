import unittest
from mimic.domain_monitor import DomainMonitor


class TestDomainMonitor(unittest.TestCase):
    def test_domain_monitor(self):
        monitor = DomainMonitor("google.com")

        self.assertEqual(monitor.domain, "google.com")

        self.assertEqual(monitor.stats(), {'acquisitions_processed': 0,
                                           'available': 0,
                                           'avg_resp_time': float('inf'),
                                           'indices': {}})

        proxy = {'host': 'localhost',
                 'proto': 'http',
                 'port': 8888,
                 'resp_time': 0,
                 'geo': 'us',
                 'anon_level': ''}
        monitor.register(proxy)