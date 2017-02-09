import unittest
from mimic.util import ProxyProps
from mimic.domain_monitor import DomainMonitor


class TestDomainMonitor(unittest.TestCase):
    def test_integration(self):
        monitor = DomainMonitor("google.com")

        self.assertEqual(monitor.domain, "google.com")

        self.assertEqual(monitor.stats(), {'acquisitions_processed': 0,
                                           'available': 0,
                                           'avg_resp_time': float('inf'),
                                           'indices': {}})

        proxy_a = ProxyProps('http', 'localhost', 8888, 0.1,
                             'us', 'transparent')
        proxy_b = ProxyProps('http', 'localhost', 8889, 0.2)

        monitor.register(proxy_a)
        monitor.register(proxy_b)

        acquired = monitor.acquire('us')
        self.assertEqual(acquired, str(proxy_a))
        self.assertIsNone(monitor.acquire('us'))
        self.assertEqual(monitor.acquire(), str(proxy_b))

        monitor.release(acquired, 0.01)
        acquired = monitor.acquire('us')
        self.assertEqual(acquired, str(proxy_a))

        monitor.release(acquired, 0.01)
        monitor.delist(str(proxy_a))

    def test_acquire_on_empty(self):
        monitor = DomainMonitor("google.com")
        self.assertIsNone(monitor.acquire())

    def test_average_response_time(self):
        monitor = DomainMonitor("google.com")
        monitor.register(ProxyProps('http', 'localhost', 8888, 0.1, 'us',
                                    'transparent'))
        monitor.register(ProxyProps('http', 'localhost', 8889, 0.3, 'us',
                                    'transparent'))

        self.assertEqual(monitor.average_response_time(), 0.2)

    def test_zeros_bug(self):
        monitor = DomainMonitor("google.com")

        a = ProxyProps('http', 'localhost', 8888, 0.0)
        b = ProxyProps('http', 'localhost', 9000, 0.0)
        monitor.register(a)
        monitor.register(b)

        for _ in range(10):
            monitor.release(monitor.acquire(), 0.0)

        self.assertTrue(True)  # I.E. Finishes

    def test_stochastic_sampling(self):
        monitor = DomainMonitor("google.com")

        a = ProxyProps('http', 'localhost', 8888, 0.1)
        b = ProxyProps('http', 'localhost', 9000, 0.2)

        counts = {str(x): 0 for x in [a, b]}
        inc = {str(x): x.resp_time for x in [a, b]}

        monitor.register(a)
        monitor.register(b)

        for _ in range(100):
            x = monitor.acquire()
            counts[str(x)] += 1
            monitor.release(x, inc[str(x)])

        self.assertGreater(counts[str(a)], counts[str(b)])


