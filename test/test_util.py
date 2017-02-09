import unittest
from itertools import product
from mimic.util import parse_and_intern_domain, ProxyProps


class TestGetAccessor(unittest.TestCase):
    def test_parse_and_intern_domain(self):
        domain = "www.yahoo.com"
        url_a = "http://www.yahoo.com/api/pages?id=1"
        url_b = "http://www.yahoo.com/api/pages?id=2"

        a, b = parse_and_intern_domain(url_a), parse_and_intern_domain(url_b)
        self.assertEqual(a, b)
        self.assertEqual(a, domain)
        self.assertIs(a, b)
        self.assertIsNot(a, domain)

    def test_proxy_props(self):
        proto, host, port = 'http', 'localhost', 8888
        a = ProxyProps(proto, host, port, 1.0, 'us', 'high')

        self.assertEqual(str(a), "http://localhost:8888".upper())
        self.assertEqual(str(a), repr(a))

        for args in product([proto, 'https'], [host, 'me'], [port, 8888]):
            if args == (proto, host, port): continue
            b = ProxyProps(*args, 1.0, 'us', 'high')
            self.assertNotEqual(a, b)

        c = ProxyProps(proto, host, port, 2.0, 'ca', 'low')
        self.assertEqual(a, c)

